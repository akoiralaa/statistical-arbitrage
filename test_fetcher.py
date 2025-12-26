#!/usr/bin/env python
"""Test data fetcher by downloading sample data."""

import sys
from datetime import datetime, timedelta
from src.utils import setup_logging, load_config, create_directories
from src.data_fetcher import DataFetcher

def main():
    # Setup
    logger = setup_logging()
    config = load_config('config.yaml')
    create_directories(config)
    
    logger.info("=" * 60)
    logger.info("Statistical Arbitrage Data Fetcher Test")
    logger.info("=" * 60)
    
    # Initialize fetcher
    fetcher = DataFetcher(config)
    
    # Use shorter date range for testing (last 6 months instead of 2 years)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=180)  # 6 months
    
    logger.info(f"\nFetching data from {start_date} to {end_date}")
    logger.info(f"Pairs: {config['pairs']}")
    logger.info(f"Timeframe: {config['backtest']['timeframe']}")
    
    # Fetch data
    try:
        data = fetcher.fetch_pairs(
            config['pairs'],
            start_date=str(start_date),
            end_date=str(end_date),
            timeframe=config['backtest']['timeframe'],
            use_cache=True
        )
        
        logger.info(f"\n✓ Successfully fetched {len(data)} pairs")
        
        # Display summary
        logger.info("\nData Summary:")
        logger.info("-" * 60)
        for pair, df in data.items():
            logger.info(f"\n{pair}:")
            logger.info(f"  Rows: {len(df)}")
            logger.info(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
            logger.info(f"  Price range: {df['close'].min():.2f} to {df['close'].max():.2f}")
            logger.info(f"  Latest price: {df['close'].iloc[-1]:.2f}")
            logger.info(f"  Columns: {list(df.columns)}")
        
        logger.info("\n" + "=" * 60)
        logger.info("Test completed successfully!")
        logger.info("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Error during test: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())