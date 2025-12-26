import pandas as pd
import numpy as np
from datetime import datetime
import logging
from src.cointegration import CointegrationTester
from src.signals import SignalGenerator, Signal

logger = logging.getLogger(__name__)

class Trade:
    """Represents a single trade."""
    
    def __init__(self, trade_id, pair, side, entry_time, entry_price, 
                 entry_quantity, hedge_ratio):
        """
        Initialize trade.
        
        Args:
            trade_id: Unique trade identifier
            pair: Tuple (asset1, asset2)
            side: 'LONG' or 'SHORT'
            entry_time: Entry timestamp
            entry_price: Entry price (spread)
            entry_quantity: Quantity of asset1
            hedge_ratio: Hedge ratio for this trade
        """
        self.trade_id = trade_id
        self.pair = pair
        self.side = side
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.entry_quantity = entry_quantity
        self.hedge_ratio = hedge_ratio
        
        self.exit_time = None
        self.exit_price = None
        self.exit_quantity = None
        self.gross_pnl = None
        self.net_pnl = None
        self.return_pct = None
    
    def close(self, exit_time, exit_price, exit_quantity, fees=0):
        """Close the trade."""
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.exit_quantity = exit_quantity
        
        # Calculate P&L as percentage of position size
        # entry_quantity is the position size in dollars
        # P&L = position_size * (spread_change % )
        if self.entry_price == 0:
            spread_change_pct = 0
        else:
            spread_change_pct = (exit_price - self.entry_price) / abs(self.entry_price)
        
        if self.side == 'LONG':
            # Long spread: profit if exit > entry
            self.gross_pnl = self.entry_quantity * spread_change_pct
        else:
            # Short spread: profit if exit < entry
            self.gross_pnl = -self.entry_quantity * spread_change_pct
        
        self.net_pnl = self.gross_pnl - fees
        self.return_pct = (self.net_pnl / self.entry_quantity) * 100 if self.entry_quantity != 0 else 0
    
    def to_dict(self):
        """Convert trade to dictionary."""
        return {
            'trade_id': self.trade_id,
            'pair': self.pair,
            'side': self.side,
            'entry_time': self.entry_time,
            'entry_price': self.entry_price,
            'exit_time': self.exit_time,
            'exit_price': self.exit_price,
            'gross_pnl': self.gross_pnl,
            'net_pnl': self.net_pnl,
            'return_pct': self.return_pct,
            'days_held': (self.exit_time - self.entry_time).days if self.exit_time else None
        }

class Backtester:
    """Backtest pairs trading strategy on historical data."""
    
    def __init__(self, config, price_data):
        """
        Initialize backtester.
        
        Args:
            config: Configuration dict
            price_data: Dict of {pair: DataFrame} with OHLCV data
        """
        self.config = config
        self.price_data = price_data
        
        self.starting_capital = config['backtest']['starting_capital']
        self.current_capital = self.starting_capital
        self.equity_curve = []
        self.trades = []
        self.open_positions = {}
        self.trade_id = 0
        
        # Initialize modules
        self.coint_tester = CointegrationTester(
            min_pvalue=config['cointegration']['min_pvalue']
        )
        self.signal_gen = SignalGenerator(
            entry_threshold=config['signals']['entry_threshold'],
            exit_threshold=config['signals']['exit_threshold']
        )
        
        # Get common dates
        self.dates = self._get_common_dates()
        logger.info(f"Backtest period: {self.dates[0]} to {self.dates[-1]} ({len(self.dates)} bars)")
    
    def _get_common_dates(self):
        """Get dates common to all pairs."""
        all_dates = [set(df['timestamp'].dt.date) for df in self.price_data.values()]
        common_dates = sorted(list(set.intersection(*all_dates)))
        return common_dates
    
    def _get_price_at_date(self, pair, date):
        """Get close price for a pair at specific date."""
        df = self.price_data[pair]
        mask = df['timestamp'].dt.date == date
        row = df[mask]
        if len(row) > 0:
            return row['close'].iloc[0]
        return None
    
    def _calculate_position_size(self, current_capital):
        """Calculate position size based on risk management."""
        risk_pct = self.config['risk']['risk_per_trade']
        max_position_pct = self.config['risk']['max_position_pct']
        
        # Risk-based sizing: risk 2% per trade
        position_size = current_capital * risk_pct
        
        # Cap at max position % of capital
        max_position = current_capital * (max_position_pct / 100)
        position_size = min(position_size, max_position)
        
        return position_size
    
    def run(self):
        """Run backtest on historical data."""
        logger.info("Starting backtest...")
        
        # Get pairs to trade
        pairs = self.config['pairs']
        
        # Iterate through each date
        for date_idx, date in enumerate(self.dates):
            # Get price data for this date
            current_prices = {}
            for pair in pairs:
                price = self._get_price_at_date(pair, date)
                if price:
                    current_prices[pair] = price
            
            if len(current_prices) < len(pairs):
                continue  # Skip if missing any prices
            
            # Process each trading pair
            for i, pair1 in enumerate(pairs):
                for pair2 in pairs[i+1:]:
                    self._process_pair(pair1, pair2, date, date_idx, current_prices)
            
            # Update equity curve
            self.equity_curve.append({
                'date': date,
                'capital': self.current_capital
            })
        
        logger.info(f"Backtest complete. Total trades: {len(self.trades)}")
        
        return self.get_results()
    
    def _process_pair(self, pair1, pair2, date, date_idx, current_prices):
        """Process a single pair."""
        # Get historical data up to current date
        df1 = self.price_data[pair1]
        df2 = self.price_data[pair2]
        
        mask1 = df1['timestamp'].dt.date <= date
        mask2 = df2['timestamp'].dt.date <= date
        
        prices1 = df1[mask1]['close'].values
        prices2 = df2[mask2]['close'].values
        
        # Need at least 252 days for cointegration test
        if len(prices1) < 252 or len(prices2) < 252:
            return
        
        # Test cointegration
        coint_result = self.coint_tester.test_cointegration(prices1, prices2)
        
        if not coint_result['cointegrated']:
            return
        
        # Calculate current spread and Z-score
        current_spread = self.coint_tester.calculate_spread(
            current_prices[pair1],
            current_prices[pair2],
            coint_result['hedge_ratio']
        )
        
        zscore = self.coint_tester.calculate_zscore(
            current_spread,
            coint_result['spread_mean'],
            coint_result['spread_std']
        )
        
        # Check if we have open position for this pair
        pair_key = (pair1, pair2)
        position = self.open_positions.get(pair_key)
        
        # Generate signal
        signal_result = self.signal_gen.generate_signal(zscore, position)
        signal = signal_result['signal']
        
        # Execute signal
        if signal == Signal.BUY and not position:
            self._open_trade(pair1, pair2, 'LONG', date, current_spread, 
                           coint_result['hedge_ratio'])
        
        elif signal == Signal.SELL and not position:
            self._open_trade(pair1, pair2, 'SHORT', date, current_spread,
                           coint_result['hedge_ratio'])
        
        elif signal == Signal.CLOSE and position:
            self._close_trade(pair1, pair2, date, current_spread)
    
    def _open_trade(self, pair1, pair2, side, date, spread, hedge_ratio):
        """Open a new trade."""
        pair_key = (pair1, pair2)
        position_size = self._calculate_position_size(self.current_capital)
        
        trade = Trade(
            self.trade_id,
            pair_key,
            side,
            date,
            spread,
            position_size,
            hedge_ratio
        )
        
        self.open_positions[pair_key] = trade
        self.trade_id += 1
        
        logger.debug(f"Opened {side} trade for {pair1}/{pair2}")
    
    def _close_trade(self, pair1, pair2, date, exit_spread):
        """Close an open trade."""
        pair_key = (pair1, pair2)
        trade = self.open_positions[pair_key]
        
        # Close trade
        fees = trade.entry_price * trade.entry_quantity * self.config['advanced']['commission_pct']
        trade.close(date, exit_spread, trade.entry_quantity, fees)
        
        # Update capital
        self.current_capital += trade.net_pnl
        
        # Record trade
        self.trades.append(trade)
        del self.open_positions[pair_key]
        
        logger.debug(f"Closed trade {trade.trade_id}: P&L = {trade.net_pnl:.2f}")
    
    def get_results(self):
        """Get backtest results."""
        equity_df = pd.DataFrame(self.equity_curve)
        
        if len(self.trades) == 0:
            logger.warning("No trades executed during backtest")
            return {
                'trades': [],
                'equity_curve': equity_df,
                'metrics': {}
            }
        
        # Convert trades to list of dicts
        trades_list = [trade.to_dict() for trade in self.trades]
        
        return {
            'trades': trades_list,
            'equity_curve': equity_df,
            'metrics': self._calculate_metrics()
        }
    
    def _calculate_metrics(self):
        """Calculate performance metrics."""
        if len(self.trades) == 0:
            return {}
        
        pnl_list = [t.net_pnl for t in self.trades if t.net_pnl is not None]
        
        if len(pnl_list) == 0:
            return {}
        
        total_pnl = sum(pnl_list)
        num_trades = len(pnl_list)
        winning_trades = len([p for p in pnl_list if p > 0])
        losing_trades = len([p for p in pnl_list if p < 0])
        
        metrics = {
            'total_trades': num_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': winning_trades / num_trades if num_trades > 0 else 0,
            'total_pnl': total_pnl,
            'avg_pnl': total_pnl / num_trades,
            'largest_win': max(pnl_list),
            'largest_loss': min(pnl_list),
            'total_return': (self.current_capital - self.starting_capital) / self.starting_capital,
            'final_capital': self.current_capital
        }
        
        return metrics