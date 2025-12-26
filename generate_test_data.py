#!/usr/bin/env python
"""Generate synthetic test data for development."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

def generate_synthetic_data(pair, num_days=730, start_price=100):
    """Generate synthetic OHLCV data for testing."""
    dates = pd.date_range(start='2023-01-01', periods=num_days, freq='1D')
    
    # Generate random walk price movement
    returns = np.random.normal(0.0005, 0.02, num_days)
    prices = start_price * np.exp(np.cumsum(returns))
    
    data = {
        'timestamp': dates,
        'open': prices * (1 + np.random.uniform(-0.01, 0.01, num_days)),
        'high': prices * (1 + np.random.uniform(0, 0.02, num_days)),
        'low': prices * (1 - np.random.uniform(0, 0.02, num_days)),
        'close': prices,
        'volume': np.random.uniform(1000000, 5000000, num_days)
    }
    
    df = pd.DataFrame(data)
    # Ensure OHLC logic
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    return df

def main():
    cache_dir = Path('./data/historical')
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    pairs = {
        'BTC/USDT': 40000,
        'ETH/USDT': 2000,
        'SOL/USDT': 100
    }
    
    for pair, start_price in pairs.items():
        df = generate_synthetic_data(pair, num_days=730, start_price=start_price)
        
        # Save to cache
        pair_name = pair.replace('/', '_')
        cache_file = cache_dir / f"{pair_name}_1d.csv"
        df.to_csv(cache_file, index=False)
        
        print(f"Generated {len(df)} rows for {pair}")
        print(f"  Price range: {df['close'].min():.2f} - {df['close'].max():.2f}")
        print(f"  Saved to {cache_file}\n")

if __name__ == '__main__':
    main()