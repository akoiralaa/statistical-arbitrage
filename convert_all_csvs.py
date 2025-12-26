import pandas as pd
import os
from pathlib import Path

input_dir = '/Users/abhiekoirala/Desktop/statistical-arbitrage/data/historical'
output_dir = './data/historical'

# Create output dir
Path(output_dir).mkdir(parents=True, exist_ok=True)

# Convert all CSVs
for file in os.listdir(input_dir):
    if file.endswith('.csv'):
        input_path = os.path.join(input_dir, file)
        
        # Read CSV
        df = pd.read_csv(input_path)
        
        # Keep only needed columns and rename
        df_converted = df[['date', 'open', 'high', 'low', 'close']].copy()
        df_converted.columns = ['timestamp', 'open', 'high', 'low', 'close']
        
        # Add volume column (set to 0 if missing)
        df_converted['volume'] = 0
        
        # Convert timestamp
        df_converted['timestamp'] = pd.to_datetime(df_converted['timestamp'])
        
        # Save
        output_file = file.replace('.csv', '_1d.csv')
        output_path = os.path.join(output_dir, output_file)
        df_converted.to_csv(output_path, index=False)
        
        print(f"Converted {file} -> {output_file}")

print("All CSVs converted!")