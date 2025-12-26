import pandas as pd
import os

data_dir = './data/historical'

for file in os.listdir(data_dir):
    if file.endswith('_1d.csv'):
        path = os.path.join(data_dir, file)
        
        # Read CSV
        df = pd.read_csv(path)
        
        # Rename 'date' to 'timestamp'
        if 'date' in df.columns:
            df = df.rename(columns={'date': 'timestamp'})
        
        # Keep only needed columns
        df = df[['timestamp', 'open', 'high', 'low', 'close']].copy()
        
        # Add volume if missing
        if 'volume' not in df.columns:
            df['volume'] = 0
        
        # Convert timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Save
        df.to_csv(path, index=False)
        print(f"Fixed {file}")

print("Done!")