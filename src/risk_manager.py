import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class RiskManager:
    """Manage position sizing, drawdown, and risk limits."""
    
    def __init__(self, config):
        """
        Initialize risk manager.
        
        Args:
            config: Configuration dict
        """
        self.max_position_pct = config['risk']['max_position_pct']
        self.risk_per_trade = config['risk']['risk_per_trade']
        self.max_drawdown_pct = config['risk']['max_drawdown_pct']
        self.stop_loss_pct = config['risk']['stop_loss_pct']
        
        self.max_capital_seen = None
        self.current_capital = None
    
    def calculate_position_size(self, capital, volatility=None):
        """
        Calculate position size based on risk parameters.
        
        Uses risk-per-trade approach: risk a fixed % per trade.
        
        Args:
            capital: Current capital
            volatility: Asset volatility (optional, for dynamic sizing)
            
        Returns:
            float: Recommended position size
        """
        self.current_capital = capital
        
        # Risk-based sizing
        risk_amount = capital * self.risk_per_trade
        
        # Cap at max position size
        max_position = capital * (self.max_position_pct / 100)
        
        position_size = min(risk_amount, max_position)
        
        return position_size
    
    def calculate_stop_loss(self, entry_price, direction='LONG'):
        """
        Calculate stop loss price.
        
        Args:
            entry_price: Entry price
            direction: 'LONG' or 'SHORT'
            
        Returns:
            float: Stop loss price
        """
        if direction == 'LONG':
            stop_loss = entry_price * (1 - self.stop_loss_pct)
        else:  # SHORT
            stop_loss = entry_price * (1 + self.stop_loss_pct)
        
        return stop_loss
    
    def check_stop_loss(self, current_price, entry_price, direction):
        """
        Check if stop loss has been hit.
        
        Args:
            current_price: Current price
            entry_price: Entry price
            direction: 'LONG' or 'SHORT'
            
        Returns:
            bool: True if stop loss hit
        """
        stop_loss = self.calculate_stop_loss(entry_price, direction)
        
        if direction == 'LONG':
            return current_price <= stop_loss
        else:  # SHORT
            return current_price >= stop_loss
    
    def check_max_drawdown(self, capital, update_max=True):
        """
        Check if maximum drawdown limit has been exceeded.
        
        Args:
            capital: Current capital
            update_max: Whether to update max capital seen
            
        Returns:
            dict with drawdown info
        """
        if self.max_capital_seen is None:
            self.max_capital_seen = capital
        
        # Update max capital if current > max
        if capital > self.max_capital_seen and update_max:
            self.max_capital_seen = capital
        
        # Calculate drawdown
        drawdown = (self.max_capital_seen - capital) / self.max_capital_seen
        drawdown_pct = drawdown * 100
        
        # Check if exceeded max
        exceeded = drawdown_pct > self.max_drawdown_pct
        
        return {
            'drawdown': drawdown,
            'drawdown_pct': drawdown_pct,
            'max_capital': self.max_capital_seen,
            'exceeded': exceeded
        }
    
    def get_kelly_fraction(self, win_rate, avg_win, avg_loss):
        """
        Calculate Kelly Criterion for optimal position sizing.
        
        Kelly % = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        
        Args:
            win_rate: Win rate (0-1)
            avg_win: Average winning trade size
            avg_loss: Average losing trade size (positive)
            
        Returns:
            float: Kelly fraction (0-1)
        """
        if avg_win == 0:
            return 0
        
        kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        
        # Kelly is aggressive, use fractional Kelly (e.g., 0.25 * kelly)
        kelly_fraction = max(0, kelly)
        
        return kelly_fraction
    
    def calculate_optimal_position_size(self, capital, win_rate, avg_win, avg_loss):
        """
        Calculate optimal position size using Kelly Criterion.
        
        Args:
            capital: Current capital
            win_rate: Win rate
            avg_win: Average win size
            avg_loss: Average loss size
            
        Returns:
            float: Recommended position size
        """
        kelly = self.get_kelly_fraction(win_rate, avg_win, avg_loss)
        
        # Use 25% of Kelly for safety
        position_fraction = kelly * 0.25
        
        position_size = capital * position_fraction
        
        # Cap at max position
        max_position = capital * (self.max_position_pct / 100)
        position_size = min(position_size, max_position)
        
        return position_size
    
    def calculate_risk_reward_ratio(self, entry_price, stop_loss, take_profit):
        """
        Calculate risk-reward ratio.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            float: Risk-reward ratio
        """
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        
        if risk == 0:
            return 0
        
        ratio = reward / risk
        return ratio
    
    def validate_trade(self, entry_price, stop_loss, take_profit, position_size, capital):
        """
        Validate trade before execution.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            position_size: Position size
            capital: Current capital
            
        Returns:
            dict with validation results
        """
        issues = []
        
        # Check position size vs capital
        if position_size > capital * (self.max_position_pct / 100):
            issues.append(f"Position size {position_size} exceeds max {self.max_position_pct}% of capital")
        
        # Check risk-reward ratio
        rr_ratio = self.calculate_risk_reward_ratio(entry_price, stop_loss, take_profit)
        if rr_ratio < 1.0:
            issues.append(f"Risk-reward ratio {rr_ratio:.2f} is less than 1.0")
        
        # Check stop loss distance
        sl_pct = abs(entry_price - stop_loss) / entry_price * 100
        if sl_pct > self.stop_loss_pct * 200:  # Too wide
            issues.append(f"Stop loss {sl_pct:.2f}% is too wide")
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'risk_reward_ratio': rr_ratio
        }