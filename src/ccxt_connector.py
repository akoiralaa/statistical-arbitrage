import ccxt
import pandas as pd
import time
from pathlib import Path
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CCXTDataFetcher:
    """Fetch historical OHLCV data from Binance via CCXT."""
    
    def __init__(self, exchange_name='binance', cache_dir='./data/historical'):
        """
        Initialize CCXT fetcher.
        
        Args:
            exchange_name: Name of exchange (binance, bybit, etc)
            cache_dir: Directory to cache downloaded data
        """
        self.exchange_name = exchange_name
        self.exchange = getattr(ccxt, exchange_name)()
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized {exchange_name} CCXT fetcher")
    
    def _get_cache_path(self, pair, timeframe):
        """Get cache file path for a pair."""
        # Convert pair BTC/USDT -> BTC_USDT
        pair_name = pair.replace('/', '_')
        return self.cache_dir / f"{pair_name}_{timeframe}.csv"
    
    def fetch_ohlcv(self, pair, timeframe='1d', start_date=None, end_date=None, 
                    use_cache=True):
        """
        Fetch OHLCV data for a trading pair.
        
        Args:
            pair: Trading pair (e.g., 'BTC/USDT')
            timeframe: Timeframe (1m, 5m, 1h, 4h, 1d)
            start_date: Start date (datetime or string YYYY-MM-DD)
            end_date: End date (datetime or string YYYY-MM-DD)
            use_cache: Whether to use cached data
            
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        # Parse dates
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        cache_path = self._get_cache_path(pair, timeframe)
        
        # Try to load from cache first
        if use_cache and cache_path.exists():
            try:
                df = pd.read_csv(cache_path, parse_dates=['timestamp'])
                # Filter by date range
                if start_date:
                    df = df[df['timestamp'] >= start_date]
                if end_date:
                    df = df[df['timestamp'] <= end_date]
                
                if len(df) > 0:
                    logger.info(f"Loaded {len(df)} rows from cache for {pair}")
                    return df
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
        
        # Fetch from exchange
        logger.info(f"Fetching {pair} data from {self.exchange_name}...")
        
        # Convert timeframe to milliseconds
        timeframe_ms = self._timeframe_to_ms(timeframe)
        
        # Start from beginning or start_date
        since = int(start_date.timestamp() * 1000) if start_date else None
        
        all_candles = []
        
        while True:
            # Fetch 500 candles at a time (CCXT default limit)
            candles = self.exchange.fetch_ohlcv(pair, timeframe, since=since, limit=500)
            
            if not candles:
                break
            
            all_candles.extend(candles)
            
            # Check if we've reached end_date
            last_candle_time = candles[-1][0]
            if end_date and last_candle_time > end_date.timestamp() * 1000:
                break
            
            # Update since for next iteration
            since = candles[-1][0] + timeframe_ms
            
            # Rate limiting to avoid hitting API limits
            time.sleep(0.1)
            
            logger.info(f"Fetched {len(all_candles)} candles so far...")
        
        # Convert to DataFrame
        df = pd.DataFrame(
            all_candles,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        
        # Convert timestamp from milliseconds to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Filter by end_date if provided
        if end_date:
            df = df[df['timestamp'] <= end_date]
        
        # Save to cache
        try:
            df.to_csv(cache_path, index=False)
            logger.info(f"Cached {len(df)} rows to {cache_path}")
        except Exception as e:
            logger.warning(f"Failed to cache data: {e}")
        
        logger.info(f"Fetched {len(df)} rows for {pair}")
        return df
    
    def _timeframe_to_ms(self, timeframe):
        """Convert timeframe string to milliseconds."""
        mapping = {
            '1m': 60 * 1000,
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000,
            '1d': 24 * 60 * 60 * 1000,
        }
        return mapping.get(timeframe, 24 * 60 * 60 * 1000)
    
    def validate_data(self, df, pair):
        """
        Validate fetched data for issues.
        
        Args:
            df: DataFrame with OHLCV data
            pair: Trading pair name
            
        Returns:
            Tuple (is_valid, errors)
        """
        errors = []
        
        # Check for empty data
        if len(df) == 0:
            errors.append(f"No data for {pair}")
            return False, errors
        
        # Check for missing values
        if df[['open', 'high', 'low', 'close', 'volume']].isnull().any().any():
            errors.append(f"Missing values in {pair} data")
        
        # Check for OHLC logical consistency
        if (df['high'] < df['low']).any():
            errors.append(f"High < Low in {pair} data")
        
        if (df['high'] < df['open']).any() or (df['high'] < df['close']).any():
            errors.append(f"High not >= Open/Close in {pair} data")
        
        if (df['low'] > df['open']).any() or (df['low'] > df['close']).any():
            errors.append(f"Low not <= Open/Close in {pair} data")
        
        # Check for duplicate timestamps
        if df['timestamp'].duplicated().any():
            errors.append(f"Duplicate timestamps in {pair} data")
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info(f"✓ Data validation passed for {pair} ({len(df)} rows)")
        else:
            logger.warning(f"✗ Data validation failed for {pair}:")
            for error in errors:
                logger.warning(f"  - {error}")
        
        return is_valid, errors
    
    def fetch_multiple_pairs(self, pairs, timeframe='1d', start_date=None, 
                            end_date=None, use_cache=True):
        """
        Fetch data for multiple pairs.
        
        Args:
            pairs: List of trading pairs
            timeframe: Timeframe for all pairs
            start_date: Start date
            end_date: End date
            use_cache: Whether to use cache
            
        Returns:
            Dict of {pair: DataFrame}
        """
        data = {}
        
        for pair in pairs:
            try:
                df = self.fetch_ohlcv(pair, timeframe, start_date, end_date, use_cache)
                is_valid, errors = self.validate_data(df, pair)
                
                if is_valid:
                    data[pair] = df
                else:
                    logger.error(f"Skipping {pair} due to validation errors")
                    
            except Exception as e:
                logger.error(f"Failed to fetch {pair}: {e}")
        
        logger.info(f"Successfully fetched data for {len(data)}/{len(pairs)} pairs")
        return data