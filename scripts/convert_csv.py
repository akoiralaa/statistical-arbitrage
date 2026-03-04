import pandas as pd

# Read the Aave CSV
df = pd.read_csv('coin_Aave.csv')

# Rename columns to match system format
df_converted = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
df_converted.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

# Convert timestamp to datetime
df_converted['timestamp'] = pd.to_datetime(df_converted['timestamp'])

# Save to data/historical folder
df_converted.to_csv('data/historical/AAVE_USDT_1d.csv', index=False)

print(f"Converted {len(df_converted)} rows")
print(df_converted.head())