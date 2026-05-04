"""
portfolio_optimizer.py
======================
Modern portfolio optimization with:
- Mean-variance optimization (Markowitz)
- Risk parity allocation
- Black-Litterman model integration
- Constraints for realistic trading
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional


def mean_variance_optimization(expected_returns: pd.Series,
                              covariance_matrix: pd.DataFrame,
                              target_return: Optional[float] = None,
                              risk_aversion: float = 1.0,
                              max_weight: float = 0.20,
                              min_weight: float = 0.0) -> Dict[str, float]:
    """Classical Markowitz mean-variance optimization."""
    
    n_assets = len(expected_returns)
    tickers = expected_returns.index.tolist()
    
    # Quadratic programming formulation
    from scipy.optimize import minimize
    
    def objective(weights):
        port_return = np.dot(weights, expected_returns)
        port_risk = np.dot(weights.T, np.dot(covariance_matrix, weights))
        return risk_aversion * port_risk - port_return
    
    # Constraints: weights sum to 1, optional target return
    constraints = [
        {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}
    ]
    
    if target_return is not None:
        constraints.append({
            'type': 'eq',
            'fun': lambda w: np.dot(w, expected_returns) - target_return
        })
    
    # Bounds: individual position limits
    bounds = [(min_weight, max_weight) for _ in range(n_assets)]
    
    # Initial guess (equal weight)
    x0 = np.ones(n_assets) / n_assets
    
    # Solve optimization
    result = minimize(objective, x0, method='SLSQP',
                     bounds=bounds, constraints=constraints)
    
    if result.success:
        weights = dict(zip(tickers, result.x))
        return {k: v for k, v in weights.items() if abs(v) > 1e-6}
    else:
        # Fallback to risk parity
        return risk_parity_allocation(covariance_matrix, max_weight=max_weight)


def risk_parity_allocation(covariance_matrix: pd.DataFrame,
                          max_weight: float = 0.20) -> Dict[str, float]:
    """Risk parity allocation - equal risk contribution."""
    
    tickers = covariance_matrix.index.tolist()
    n_assets = len(tickers)
    
    # Inverse volatility weighting
    volatilities = np.sqrt(np.diag(covariance_matrix))
    inv_vol = 1.0 / (volatilities + 1e-12)
    weights = inv_vol / np.sum(inv_vol)
    
    # Apply position limits
    weights = np.clip(weights, 0, max_weight)
    weights = weights / np.sum(weights)  # Renormalize
    
    return dict(zip(tickers, weights))


def black_litterman_allocation(prior_weights: Dict[str, float],
                              covariance_matrix: pd.DataFrame,
                              views: Dict[str, float],
                              view_confidences: Dict[str, float],
                              tau: float = 0.05) -> Dict[str, float]:
    """Black-Litterman model combining market equilibrium with views."""
    
    tickers = list(prior_weights.keys())
    n_assets = len(tickers)
    
    # Market equilibrium returns (implied from prior weights)
    market_returns = np.dot(covariance_matrix, list(prior_weights.values()))
    
    # Create view matrices
    P = []  # Pick matrix
    Q = []  # View returns
    Omega = []  # View uncertainties
    
    for ticker, view_return in views.items():
        if ticker in tickers:
            idx = tickers.index(ticker)
            p_vec = np.zeros(n_assets)
            p_vec[idx] = 1.0
            P.append(p_vec)
            Q.append(view_return)
            Omega.append(view_confidences.get(ticker, 0.5))
    
    if not P:
        return prior_weights
    
    P = np.array(P)
    Q = np.array(Q)
    Omega = np.diag(Omega)
    
    # Black-Litterman formula
    tau_sigma = tau * covariance_matrix
    
    # Posterior covariance
    posterior_cov = np.linalg.inv(np.linalg.inv(tau_sigma) + P.T @ np.linalg.inv(Omega) @ P)
    
    # Posterior returns
    posterior_returns = posterior_cov @ (
        np.linalg.inv(tau_sigma) @ market_returns + P.T @ np.linalg.inv(Omega) @ Q
    )
    
    # Convert to weights using mean-variance optimization
    return mean_variance_optimization(
        pd.Series(posterior_returns, index=tickers),
        posterior_cov,
        max_weight=0.25
    )


def hierarchical_risk_parity(covariance_matrix: pd.DataFrame,
                           max_weight: float = 0.20) -> Dict[str, float]:
    """Hierarchical Risk Parity - robust to estimation error."""
    
    from scipy.cluster.hierarchy import linkage, dendrogram
    from scipy.spatial.distance import squareform
    
    # Convert covariance to correlation distance
    corr_matrix = covariance_matrix.copy()
    std_devs = np.sqrt(np.diag(covariance_matrix))
    for i in range(len(corr_matrix)):
        for j in range(len(corr_matrix)):
            corr_matrix.iloc[i, j] = covariance_matrix.iloc[i, j] / (std_devs[i] * std_devs[j] + 1e-12)
    
    # Distance matrix
    distance_matrix = np.sqrt(2 * (1 - corr_matrix))
    
    # Hierarchical clustering
    dist_array = squareform(distance_matrix.values)
    linkage_matrix = linkage(dist_array, method='ward')
    
    # TODO: Implement full HRP algorithm
    # For now, fallback to simple risk parity
    return risk_parity_allocation(covariance_matrix, max_weight=max_weight)


def calculate_turnover_penalty(current_weights: Dict[str, float],
                              new_weights: Dict[str, float],
                              turnover_cost: float = 0.001) -> float:
    """Calculate turnover cost penalty for rebalancing."""
    
    tickers = set(current_weights.keys()) | set(new_weights.keys())
    turnover = 0.0
    
    for ticker in tickers:
        current = current_weights.get(ticker, 0.0)
        new = new_weights.get(ticker, 0.0)
        turnover += abs(new - current)
    
    return turnover * turnover_cost


def optimize_with_constraints(expected_returns: pd.Series,
                             covariance_matrix: pd.DataFrame,
                             current_weights: Dict[str, float],
                             turnover_limit: float = 0.10,
                             max_weight: float = 0.20,
                             min_weight: float = 0.0) -> Dict[str, float]:
    """Optimize with realistic trading constraints."""
    
    n_assets = len(expected_returns)
    tickers = expected_returns.index.tolist()
    
    from scipy.optimize import minimize
    
    def objective(weights):
        port_return = np.dot(weights, expected_returns)
        port_risk = np.dot(weights.T, np.dot(covariance_matrix, weights))
        
        # Turnover penalty
        current_vec = np.array([current_weights.get(t, 0.0) for t in tickers])
        turnover = np.sum(np.abs(weights - current_vec))
        turnover_penalty = 1000 * max(0, turnover - turnover_limit) ** 2
        
        return 1.0 * port_risk - port_return + turnover_penalty
    
    constraints = [
        {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}
    ]
    
    bounds = [(min_weight, max_weight) for _ in range(n_assets)]
    
    # Start from current weights
    x0 = np.array([current_weights.get(t, 0.0) for t in tickers])
    
    result = minimize(objective, x0, method='SLSQP',
                     bounds=bounds, constraints=constraints)
    
    if result.success:
        weights = dict(zip(tickers, result.x))
        return {k: v for k, v in weights.items() if abs(v) > 1e-6}
    else:
        return current_weights  # No change if optimization fails


def calculate_portfolio_metrics(weights: Dict[str, float],
                               expected_returns: pd.Series,
                               covariance_matrix: pd.DataFrame) -> Dict:
    """Calculate portfolio performance metrics."""
    
    tickers = list(weights.keys())
    w_vec = np.array([weights[t] for t in tickers])
    ret_vec = expected_returns[tickers].values
    cov_mat = covariance_matrix.loc[tickers, tickers].values
    
    port_return = np.dot(w_vec, ret_vec)
    port_risk = np.sqrt(np.dot(w_vec.T, np.dot(cov_mat, w_vec)))
    sharpe = port_return / (port_risk + 1e-12)
    
    # Diversification ratio
    weighted_vol = np.sum(np.abs(w_vec) * np.sqrt(np.diag(cov_mat)))
    diversification = weighted_vol / (port_risk + 1e-12)
    
    return {
        'expected_return': float(port_return),
        'expected_risk': float(port_risk),
        'sharpe_ratio': float(sharpe),
        'diversification_ratio': float(diversification),
        'effective_n': float(1.0 / np.sum(w_vec ** 2))  # Inverse Herfindahl
    }