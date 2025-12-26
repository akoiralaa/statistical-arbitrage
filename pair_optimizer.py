#!/usr/bin/env python
"""Test multiple pair combinations to find best performers."""

import pandas as pd
import logging
from datetime import datetime
from src.utils import setup_logging, load_config, create_directories
from src.data_fetcher import DataFetcher
from src.backtester import Backtester
from src.analyzer import PerformanceAnalyzer

logger = setup_logging()

def test_pair_combination(config, pair1, pair2, price_data):
    """Test a single pair combination."""
    
    # Update config for this pair
    config['pairs'] = [pair1, pair2]
    
    try:
        # Run backtest
        backtester = Backtester(config, price_data)
        backtest_results = backtester.run()
        
        # Analyze results
        analyzer = PerformanceAnalyzer()
        metrics = analyzer.analyze_backtest(
            backtest_results,
            config['backtest']['starting_capital']
        )
        
        return {
            'pair1': pair1,
            'pair2': pair2,
            'total_trades': metrics.get('total_trades', 0),
            'win_rate': metrics.get('win_rate', 0),
            'total_return_pct': metrics.get('total_return_pct', 0),
            'sharpe_ratio': metrics.get('sharpe_ratio', 0),
            'max_drawdown_pct': metrics.get('max_drawdown_pct', 0),
            'profit_factor': metrics.get('profit_factor', 0),
            'annualized_return_pct': metrics.get('annualized_return_pct', 0),
        }
    except Exception as e:
        logger.error(f"Error testing {pair1}/{pair2}: {e}")
        return None

def main():
    """Run pair optimization."""
    logger.info("=" * 70)
    logger.info("PAIR COMBINATION OPTIMIZER")
    logger.info("=" * 70)
    
    # Load config and data
    config = load_config('config.yaml')
    create_directories(config)
    
    fetcher = DataFetcher(config)
    
    start_date = config['backtest']['start_date']
    end_date = config['backtest']['end_date']
    timeframe = config['backtest']['timeframe']
    
    # Pairs to test
    pairs_to_test = [
        ('BTC/USDT', 'ETH/USDT'),
        ('BTC/USDT', 'BTC/ETH'),
        ('BTC/USDT', 'SOL/USDT'),
        ('BTC/USDT', 'BNB/USDT'),
        ('ETH/USDT', 'BTC/ETH'),
        ('ETH/USDT', 'SOL/USDT'),
        ('ETH/USDT', 'BNB/USDT'),
        ('BTC/ETH', 'SOL/USDT'),
        ('BTC/ETH', 'BNB/USDT'),
        ('SOL/USDT', 'BNB/USDT'),
    ]
    
    logger.info(f"\nTesting {len(pairs_to_test)} pair combinations...")
    logger.info(f"Date range: {start_date} to {end_date}\n")
    
    results = []
    
    for i, (pair1, pair2) in enumerate(pairs_to_test, 1):
        logger.info(f"[{i}/{len(pairs_to_test)}] Testing {pair1} vs {pair2}...")
        
        # Fetch data for this pair combination
        price_data = fetcher.fetch_pairs(
            [pair1, pair2],
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe,
            use_cache=True
        )
        
        if len(price_data) < 2:
            logger.warning(f"  Skipping - missing data")
            continue
        
        # Test this combination
        result = test_pair_combination(config, pair1, pair2, price_data)
        
        if result:
            results.append(result)
            logger.info(f"  ✓ {result['total_trades']} trades | "
                       f"Return: {result['total_return_pct']:.2f}% | "
                       f"Sharpe: {result['sharpe_ratio']:.2f}")
    
    # Print results summary
    logger.info("\n" + "=" * 70)
    logger.info("RESULTS SUMMARY")
    logger.info("=" * 70)
    
    if not results:
        logger.info("No results to display")
        return
    
    # Sort by Sharpe ratio
    results_sorted = sorted(results, key=lambda x: x['sharpe_ratio'], reverse=True)
    
    # Print table
    logger.info(f"\n{'Pair 1':<12} {'Pair 2':<12} {'Trades':>6} {'Win%':>6} {'Return%':>10} {'Sharpe':>8} {'MaxDD%':>8}")
    logger.info("-" * 70)
    
    for r in results_sorted:
        logger.info(
            f"{r['pair1']:<12} {r['pair2']:<12} {r['total_trades']:>6} "
            f"{r['win_rate']*100:>5.1f}% {r['total_return_pct']:>9.2f}% "
            f"{r['sharpe_ratio']:>8.2f} {r['max_drawdown_pct']:>7.2f}%"
        )
    
    # Best pair
    best = results_sorted[0]
    logger.info("\n" + "=" * 70)
    logger.info(f"BEST PAIR: {best['pair1']} vs {best['pair2']}")
    logger.info(f"Sharpe Ratio: {best['sharpe_ratio']:.2f}")
    logger.info(f"Total Return: {best['total_return_pct']:.2f}%")
    logger.info(f"Win Rate: {best['win_rate']*100:.1f}%")
    logger.info(f"Max Drawdown: {best['max_drawdown_pct']:.2f}%")
    logger.info(f"Trades: {best['total_trades']}")
    logger.info("=" * 70)
    
    # Save results to CSV
    df_results = pd.DataFrame(results_sorted)
    df_results.to_csv('pair_optimization_results.csv', index=False)
    logger.info(f"\nResults saved to pair_optimization_results.csv")

if __name__ == '__main__':
    main()