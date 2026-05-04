"""
risk_manager.py
===============
Advanced risk management system with:
- Volatility targeting and position sizing
- Correlation-aware portfolio construction
- Dynamic stop-loss and take-profit
- Drawdown-based position reduction
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional


class RiskManager:
    def __init__(self,
                 target_vol: float = 0.15,
                 max_position: float = 0.20,
                 max_leverage: float = 1.5,
                 stop_loss: float = 0.08,
                 take_profit: float = 0.12,
                 max_drawdown: float = 0.25,
                 corr_threshold: float = 0.7):
        self.target_vol = target_vol
        self.max_position = max_position
        self.max_leverage = max_leverage
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.max_drawdown = max_drawdown
        self.corr_threshold = corr_threshold
        
        self.portfolio_drawdown = 0.0
        self.max_seen_drawdown = 0.0
        self.position_history = []
        
    def calculate_volatility_target_weights(self,
                                          signals: Dict[str, float],
                                          recent_vols: Dict[str, float],
                                          recent_returns: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        """Calculate volatility-targeted position weights with correlation adjustment."""
        
        # Basic volatility scaling
        total_risk = sum(abs(sig) * vol for sig, vol in zip(signals.values(), recent_vols.values()))
        
        if total_risk == 0:
            return {ticker: 0.0 for ticker in signals}
        
        scale_factor = min(self.target_vol / (total_risk + 1e-12), self.max_leverage)
        
        # Apply correlation adjustment if returns data available
        if recent_returns is not None and len(recent_returns) > 30:
            corr_matrix = recent_returns.corr()
            adjusted_signals = self._adjust_for_correlation(signals, corr_matrix)
        else:
            adjusted_signals = signals
        
        weights = {}
        for ticker, signal in adjusted_signals.items():
            scaled_pos = signal * scale_factor
            
            # Apply drawdown-based reduction
            if self.max_seen_drawdown > 0.15:
                reduction = 1.0 - min(1.0, self.max_seen_drawdown / self.max_drawdown)
                scaled_pos *= reduction
            
            # Apply individual position cap
            weights[ticker] = np.clip(scaled_pos, -self.max_position, self.max_position)
        
        return weights
    
    def _adjust_for_correlation(self, signals: Dict[str, float], corr_matrix: pd.DataFrame) -> Dict[str, float]:
        """Reduce positions for highly correlated assets."""
        adjusted = signals.copy()
        tickers = list(signals.keys())
        
        for i, ticker1 in enumerate(tickers):
            if abs(signals[ticker1]) < 0.1:
                continue
                
            for ticker2 in tickers[i+1:]:
                if abs(signals[ticker2]) < 0.1:
                    continue
                    
                if ticker1 in corr_matrix.columns and ticker2 in corr_matrix.index:
                    corr = corr_matrix.loc[ticker1, ticker2]
                    if abs(corr) > self.corr_threshold:
                        # Reduce both positions proportionally
                        reduction = 1.0 - (abs(corr) - self.corr_threshold) / (1.0 - self.corr_threshold)
                        adjusted[ticker1] *= reduction
                        adjusted[ticker2] *= reduction
        
        return adjusted
    
    def apply_stop_loss_take_profit(self,
                                  current_weights: Dict[str, float],
                                  entry_prices: Dict[str, float],
                                  current_prices: Dict[str, float]) -> Dict[str, float]:
        """Apply stop-loss and take-profit logic to positions."""
        new_weights = current_weights.copy()
        
        for ticker, weight in current_weights.items():
            if abs(weight) < 0.01 or ticker not in entry_prices:
                continue
                
            entry = entry_prices[ticker]
            current = current_prices[ticker]
            
            if weight > 0:  # Long position
                ret = (current - entry) / entry
                if ret <= -self.stop_loss:
                    new_weights[ticker] = 0.0
                elif ret >= self.take_profit:
                    # Take partial profits
                    new_weights[ticker] = weight * 0.5
            
            elif weight < 0:  # Short position
                ret = (entry - current) / entry
                if ret <= -self.stop_loss:
                    new_weights[ticker] = 0.0
                elif ret >= self.take_profit:
                    new_weights[ticker] = weight * 0.5
        
        return new_weights
    
    def update_drawdown(self, current_equity: float, peak_equity: float):
        """Update drawdown tracking and return position reduction factor."""
        self.portfolio_drawdown = 1.0 - (current_equity / peak_equity)
        self.max_seen_drawdown = max(self.max_seen_drawdown, self.portfolio_drawdown)
        
        # Calculate position reduction based on drawdown
        if self.max_seen_drawdown > 0.1:
            reduction = 1.0 - min(1.0, self.max_seen_drawdown / self.max_drawdown)
            return reduction
        return 1.0
    
    def should_stop_trading(self) -> bool:
        """Check if trading should stop due to excessive drawdown."""
        return self.max_seen_drawdown >= self.max_drawdown
    
    def get_risk_report(self) -> Dict:
        """Generate current risk report."""
        return {
            "current_drawdown": self.portfolio_drawdown,
            "max_drawdown": self.max_seen_drawdown,
            "trading_active": not self.should_stop_trading(),
            "position_count": len([w for w in self.position_history[-1].values() if abs(w) > 0.01]) if self.position_history else 0
        }


def calculate_position_sizes(signals: Dict[str, float],
                            volatilities: Dict[str, float],
                            correlations: Optional[pd.DataFrame] = None,
                            target_vol: float = 0.15,
                            max_position: float = 0.20) -> Dict[str, float]:
    """Calculate optimal position sizes using risk parity principles."""
    
    # Calculate risk contributions
    risk_contributions = {}
    for ticker, signal in signals.items():
        if abs(signal) < 0.1:
            risk_contributions[ticker] = 0.0
        else:
            risk_contributions[ticker] = abs(signal) * volatilities[ticker]
    
    total_risk = sum(risk_contributions.values())
    
    if total_risk == 0:
        return {ticker: 0.0 for ticker in signals}
    
    # Calculate naive weights
    weights = {}
    for ticker, risk_contrib in risk_contributions.items():
        if risk_contrib > 0:
            weights[ticker] = (risk_contrib / total_risk) * np.sign(signals[ticker])
        else:
            weights[ticker] = 0.0
    
    # Apply correlation adjustment if available
    if correlations is not None:
        weights = _adjust_weights_for_correlation(weights, correlations)
    
    # Scale to target volatility
    portfolio_vol = calculate_portfolio_volatility(weights, volatilities, correlations)
    scale_factor = min(target_vol / (portfolio_vol + 1e-12), 2.0)
    
    final_weights = {}
    for ticker, weight in weights.items():
        scaled = weight * scale_factor
        final_weights[ticker] = np.clip(scaled, -max_position, max_position)
    
    return final_weights


def _adjust_weights_for_correlation(weights: Dict[str, float], corr_matrix: pd.DataFrame) -> Dict[str, float]:
    """Reduce weights for highly correlated assets."""
    adjusted = weights.copy()
    tickers = list(weights.keys())
    
    for i, ticker1 in enumerate(tickers):
        if abs(weights[ticker1]) < 0.01:
            continue
            
        for ticker2 in tickers[i+1:]:
            if abs(weights[ticker2]) < 0.01:
                continue
                
            if ticker1 in corr_matrix.columns and ticker2 in corr_matrix.index:
                corr = corr_matrix.loc[ticker1, ticker2]
                if abs(corr) > 0.7:
                    # Reduce both positions
                    reduction = 0.7 / abs(corr)
                    adjusted[ticker1] *= reduction
                    adjusted[ticker2] *= reduction
    
    return adjusted


def calculate_portfolio_volatility(weights: Dict[str, float],
                                  volatilities: Dict[str, float],
                                  correlations: Optional[pd.DataFrame] = None) -> float:
    """Calculate portfolio volatility."""
    tickers = list(weights.keys())
    
    if not tickers:
        return 0.0
    
    # If no correlation matrix, assume average correlation of 0.3
    if correlations is None:
        var = sum((w * volatilities[ticker]) ** 2 for ticker, w in weights.items())
        cov = 0.3 * sum(
            abs(weights[ticker_i] * weights[ticker_j] * volatilities[ticker_i] * volatilities[ticker_j])
            for i, ticker_i in enumerate(tickers)
            for j, ticker_j in enumerate(tickers)
            if i < j
        )
        return np.sqrt(var + 2 * cov)
    
    # Use actual correlation matrix
    var = 0.0
    for i, ticker_i in enumerate(tickers):
        for j, ticker_j in enumerate(tickers):
            if ticker_i in correlations.columns and ticker_j in correlations.index:
                corr = correlations.loc[ticker_i, ticker_j]
                var += (weights[ticker_i] * volatilities[ticker_i] * 
                        weights[ticker_j] * volatilities[ticker_j] * corr)
    
    return np.sqrt(max(0, var))


def calculate_value_at_risk(weights: Dict[str, float],
                           volatilities: Dict[str, float],
                           correlations: Optional[pd.DataFrame] = None,
                           confidence: float = 0.95,
                           horizon: int = 1) -> float:
    """Calculate Value at Risk for the portfolio."""
    portfolio_vol = calculate_portfolio_volatility(weights, volatilities, correlations)
    
    # Z-score for confidence level
    from scipy.stats import norm
    z = norm.ppf(confidence)
    
    return z * portfolio_vol * np.sqrt(horizon / 252.0)