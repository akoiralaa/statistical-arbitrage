import logging
from src.ccxt_connector import CCXTDataFetcher

logger = logging.getLogger(__name__)

class DataFetcher:
    """
    Unified data fetcher interface that can switch between sources
    (CCXT for backtesting, Alpaca for live trading).
    """
    
    def __init__(self, config):
        """
        Initialize data fetcher.
        
        Args:
            config: Configuration dict
        """
        self.config = config
        self.source = config['data']['source']
        
        if self.source == 'ccxt':
            exchange = config['data']['exchange']
            cache_dir = config['data']['cache_dir']
            self.fetcher = CCXTDataFetcher(exchange, cache_dir)
            logger.info(f"Initialized {exchange} CCXT fetcher")
        else:
            raise ValueError(f"Unknown data source: {self.source}")
    
    def fetch_pairs(self, pairs, start_date, end_date, timeframe='1d', use_cache=True):
        """
        Fetch data for multiple trading pairs.
        
        Args:
            pairs: List of trading pairs (e.g., ['BTC/USDT', 'ETH/USDT'])
            start_date: Start date (string YYYY-MM-DD or datetime)
            end_date: End date (string YYYY-MM-DD or datetime)
            timeframe: Timeframe (1m, 5m, 1h, 4h, 1d)
            use_cache: Whether to use cached data
            
        Returns:
            Dict of {pair: DataFrame}
        """
        logger.info(f"Fetching {len(pairs)} pairs from {start_date} to {end_date}")
        
        data = self.fetcher.fetch_multiple_pairs(
            pairs,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            use_cache=use_cache
        )
        
        return data
    
    def fetch_single_pair(self, pair, start_date, end_date, timeframe='1d', use_cache=True):
        """
        Fetch data for a single trading pair.
        
        Args:
            pair: Trading pair
            start_date: Start date
            end_date: End date
            timeframe: Timeframe
            use_cache: Whether to use cached data
            
        Returns:
            DataFrame
        """
        return self.fetcher.fetch_ohlcv(
            pair,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            use_cache=use_cache
        )