"""
run_backtest.py
===============
Main script to run comprehensive backtests with all risk management features.
Combines signals from multiple models with advanced portfolio optimization.
"""

import os
import sys
import json
import argparse
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from backtest_engine import run_portfolio_backtest
from risk_manager import RiskManager
from portfolio_optimizer import mean_variance_optimization, risk_parity_allocation


def parse_args():
    p = argparse.ArgumentParser(description="Run comprehensive portfolio backtest")
    p.add_argument("--tickers", nargs="+", default=["RELIANCE.NS", "HDFCBANK.NS", "TCS.NS", "INFY.NS", "ICICIBANK.NS"])
    p.add_argument("--start", default="2020-01-01")
    p.add_argument("--end", default=None)
    p.add_argument("--window", type=int, default=60)
    p.add_argument("--horizon", type=int, default=1)
    p.add_argument("--model-dir", default="../backend/models")
    p.add_argument("--allocation", choices=["mv", "rp", "equal"], default="rp",
                  help="Portfolio allocation method: mv=mean-variance, rp=risk-parity, equal=equal weight")
    p.add_argument("--target-vol", type=float, default=0.15)
    p.add_argument("--max-position", type=float, default=0.20)
    p.add_argument("--transaction-cost", type=float, default=0.0005)
    p.add_argument("--slippage", type=float, default=0.0002)
    p.add_argument("--rebalance-days", type=int, default=5)
    p.add_argument("--output", default="../backtest_results")
    return p.parse_args()


def load_all_predictions(tickers: List[str], model_dir: str, start_date: str, window: int, horizon: int) -> Dict:
    """Load predictions for all tickers and align dates."""
    
    all_data = {}
    for ticker in tickers:
        try:
            from backtest_engine import load_model_predictions
            probs, returns, dates = load_model_predictions(ticker, model_dir, start_date, window, horizon)
            all_data[ticker] = {
                'probs': probs,
                'returns': returns,
                'dates': dates
            }
        except Exception as e:
            print(f"Warning: Could not load {ticker}: {e}")
    
    return all_data


def calculate_portfolio_allocation(signals: Dict[str, float], 
                                  recent_vols: Dict[str, float],
                                  recent_returns: Optional[pd.DataFrame] = None,
                                  method: str = "rp") -> Dict[str, float]:
    """Calculate portfolio allocation using specified method."""
    
    if method == "equal":
        # Equal weight among active signals
        active_tickers = [t for t, s in signals.items() if abs(s) > 0.1]
        if not active_tickers:
            return {t: 0.0 for t in signals}
        weight = 1.0 / len(active_tickers)
        return {t: weight * np.sign(signals[t]) for t in active_tickers}
    
    elif method == "mv" and recent_returns is not None:
        # Mean-variance optimization
        expected_returns = pd.Series({
            t: signals[t] * recent_vols[t] / np.sqrt(252) for t in signals
        })
        
        # Simple covariance estimate
        cov_matrix = recent_returns.cov() * 252
        
        return mean_variance_optimization(
            expected_returns,
            cov_matrix,
            max_weight=0.25
        )
    
    else:
        # Risk parity (default)
        from risk_manager import calculate_position_sizes
        return calculate_position_sizes(
            signals,
            recent_vols,
            recent_returns.corr() if recent_returns is not None else None,
            target_vol=0.15,
            max_position=0.20
        )


def run_comprehensive_backtest(args) -> Dict:
    """Run backtest with multiple allocation methods and risk management."""
    
    # Load predictions
    ticker_data = load_all_predictions(args.tickers, args.model_dir, args.start, args.window, args.horizon)
    
    if not ticker_data:
        raise ValueError("No valid ticker data found")
    
    # Find common dates
    common_dates = set.intersection(*[set(data['dates']) for data in ticker_data.values()])
    common_dates = sorted(common_dates)
    
    # Initialize portfolio
    portfolio = {
        'equity': [1.0],
        'positions': {ticker: 0.0 for ticker in ticker_data},
        'cash': 1.0,
        'leverage': 0.0
    }
    
    risk_manager = RiskManager(
        target_vol=args.target_vol,
        max_position=args.max_position,
        max_leverage=1.5,
        stop_loss=0.08,
        take_profit=0.12,
        max_drawdown=0.25
    )
    
    # Track performance
    daily_returns = []
    trades = []
    allocations = []
    
    for i, date in enumerate(common_dates):
        if i < 60:  # Warm-up period
            continue
        
        # Get signals
        signals = {}
        for ticker, data in ticker_data.items():
            prob = data['probs'][i]
            if prob >= 0.55:
                signals[ticker] = 1.0
            elif prob <= 0.45:
                signals[ticker] = -1.0
            else:
                signals[ticker] = 0.0
        
        # Calculate recent volatility (20-day)
        recent_vols = {}
        recent_returns_df = pd.DataFrame()
        
        for ticker, data in ticker_data.items():
            start_idx = max(0, i - 20)
            rets = data['returns'][start_idx:i]
            recent_vols[ticker] = np.std(rets) * np.sqrt(252) if len(rets) > 5 else 0.20
            recent_returns_df[ticker] = data['returns'][max(0, i-60):i]
        
        # Rebalance periodically
        if i % args.rebalance_days == 0:
            target_weights = calculate_portfolio_allocation(
                signals, recent_vols, recent_returns_df, args.allocation
            )
            
            # Apply risk management
            target_weights = risk_manager.calculate_volatility_target_weights(
                target_weights, recent_vols, recent_returns_df
            )
        else:
            target_weights = portfolio['positions']
        
        # Execute trades
        day_pnl = 0.0
        for ticker, target_weight in target_weights.items():
            current_weight = portfolio['positions'].get(ticker, 0.0)
            
            if abs(target_weight - current_weight) > 0.005:
                trade_size = target_weight - current_weight
                cost = abs(trade_size) * (args.transaction_cost + args.slippage)
                portfolio['cash'] -= cost
                portfolio['positions'][ticker] = target_weight
                
                trades.append({
                    'date': date,
                    'ticker': ticker,
                    'size': trade_size,
                    'cost': cost
                })
            
            # Calculate PnL
            ret = ticker_data[ticker]['returns'][i]
            day_pnl += portfolio['positions'][ticker] * ret
        
        # Update portfolio
        total_equity = portfolio['cash'] + sum(abs(w) for w in portfolio['positions'].values())
        portfolio['equity'].append(total_equity)
        daily_returns.append(day_pnl)
        
        # Update risk manager
        risk_manager.update_drawdown(total_equity, max(portfolio['equity']))
        
        # Stop if max drawdown breached
        if risk_manager.should_stop_trading():
            print(f"Trading stopped at {date}: Max drawdown breached")
            break
    
    # Calculate final metrics
    equity = np.array(portfolio['equity'])
    returns = np.diff(equity) / equity[:-1]
    
    total_return = equity[-1] - 1.0
    sharpe = np.mean(returns) / (np.std(returns) + 1e-12) * np.sqrt(252)
    sortino = np.mean(returns) / (np.std(returns[returns < 0]) + 1e-12) * np.sqrt(252)
    max_dd = 1.0 - np.min(equity) / np.max(equity)
    
    report = {
        'tickers': args.tickers,
        'allocation_method': args.allocation,
        'period': f"{common_dates[0]} to {common_dates[-1]}",
        'total_return': float(total_return),
        'annualized_return': float((1 + total_return) ** (252 / len(returns)) - 1),
        'sharpe_ratio': float(sharpe),
        'sortino_ratio': float(sortino),
        'max_drawdown': float(max_dd),
        'final_equity': float(equity[-1]),
        'total_trades': len(trades),
        'avg_daily_turnover': float(np.mean([abs(t['size']) for t in trades]) if trades else 0),
        'total_costs': float(sum(t['cost'] for t in trades)),
        'risk_parameters': args.__dict__
    }
    
    # Save results
    os.makedirs(args.output, exist_ok=True)
    result_path = os.path.join(args.output, f"backtest_report_{args.allocation}.json")
    with open(result_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    equity_path = os.path.join(args.output, f"equity_curve_{args.allocation}.csv")
    pd.DataFrame({
        'date': common_dates[:len(equity)],
        'equity': equity
    }).to_csv(equity_path, index=False)
    
    print(f"Backtest complete. Results saved to {args.output}")
    print(json.dumps(report, indent=2))
    
    return report


def compare_allocation_methods(args):
    """Compare different allocation methods."""
    
    methods = ['equal', 'rp', 'mv']
    results = {}
    
    for method in methods:
        print(f"\n=== Running {method.upper()} allocation ===")
        args.allocation = method
        results[method] = run_comprehensive_backtest(args)
    
    # Create comparison report
    comparison = {
        method: {
            'annualized_return': result['annualized_return'],
            'sharpe_ratio': result['sharpe_ratio'],
            'max_drawdown': result['max_drawdown'],
            'final_equity': result['final_equity']
        }
        for method, result in results.items()
    }
    
    comp_path = os.path.join(args.output, "allocation_comparison.json")
    with open(comp_path, 'w') as f:
        json.dump(comparison, f, indent=2)
    
    print("\n=== Allocation Method Comparison ===")
    for method, metrics in comparison.items():
        print(f"{method.upper()}: {metrics['annualized_return']:.1%} return, "
              f"Sharpe {metrics['sharpe_ratio']:.2f}, "
              f"MaxDD {metrics['max_drawdown']:.1%}")
    
    return comparison


def main():
    args = parse_args()
    
    if args.allocation == "compare":
        compare_allocation_methods(args)
    else:
        run_comprehensive_backtest(args)


if __name__ == "__main__":
    main()