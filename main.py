#!/usr/bin/env python
"""Main entry point for statistical arbitrage pairs trading system."""

import sys
import logging
from datetime import datetime
from src.utils import setup_logging, load_config, create_directories
from src.data_fetcher import DataFetcher
from src.backtester import Backtester
from src.analyzer import PerformanceAnalyzer

def main():
    """Run the complete statistical arbitrage system."""
    
    # Setup
    logger = setup_logging()
    config = load_config('config.yaml')
    create_directories(config)
    
    logger.info("=" * 70)
    logger.info("STATISTICAL ARBITRAGE PAIRS TRADING SYSTEM")
    logger.info("=" * 70)
    logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Step 1: Fetch data
        logger.info("\n[1/4] Fetching historical data...")
        fetcher = DataFetcher(config)
        
        start_date = config['backtest']['start_date']
        end_date = config['backtest']['end_date']
        timeframe = config['backtest']['timeframe']
        pairs = config['pairs']
        
        price_data = fetcher.fetch_pairs(
            pairs,
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe,
            use_cache=True
        )
        
        if len(price_data) == 0:
            logger.error("Failed to fetch any data. Exiting.")
            return 1
        
        logger.info(f"✓ Successfully fetched {len(price_data)} pairs")
        
        # Step 2: Run backtest
        logger.info("\n[2/4] Running backtest...")
        backtester = Backtester(config, price_data)
        backtest_results = backtester.run()
        
        logger.info(f"✓ Backtest complete. Executed {len(backtest_results['trades'])} trades")
        
        # Step 3: Analyze results
        logger.info("\n[3/4] Analyzing results...")
        analyzer = PerformanceAnalyzer()
        metrics = analyzer.analyze_backtest(
            backtest_results,
            config['backtest']['starting_capital']
        )
        
        # Step 4: Print report
        logger.info("\n[4/4] Generating report...")
        analyzer.print_report(metrics)
        
        # Print success
        logger.info("\n" + "=" * 70)
        logger.info("BACKTEST COMPLETED SUCCESSFULLY")
        logger.info("=" * 70)
        logger.info(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())