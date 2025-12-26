import logging
from enum import Enum

logger = logging.getLogger(__name__)

class Signal(Enum):
    """Trading signals."""
    BUY = 'BUY'
    SELL = 'SELL'
    CLOSE = 'CLOSE'
    HOLD = 'HOLD'

class SignalGenerator:
    """Generate trading signals based on Z-score of spread."""
    
    def __init__(self, entry_threshold=2.0, exit_threshold=0.5):
        """
        Initialize signal generator.
        
        Args:
            entry_threshold: Z-score threshold for entry signals (default 2.0)
            exit_threshold: Z-score threshold for exit signals (default 0.5)
        """
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold
    
    def generate_signal(self, zscore, position_open=None):
        """
        Generate trading signal based on Z-score.
        
        Signal Logic:
        - If |zscore| > entry_threshold and no position:
          - If zscore < -entry_threshold: BUY (long asset1, short asset2)
          - If zscore > entry_threshold: SELL (short asset1, long asset2)
        
        - If position_open and |zscore| < exit_threshold:
          - CLOSE (take profit, spread reverted to mean)
        
        - Otherwise: HOLD
        
        Args:
            zscore: Current Z-score of spread
            position_open: Current position (None, 'LONG', 'SHORT')
            
        Returns:
            dict with signal info
        """
        signal = Signal.HOLD
        confidence = 0.0
        
        # Exit signal: close position when spread reverts to mean
        if position_open and abs(zscore) < self.exit_threshold:
            signal = Signal.CLOSE
            confidence = 1.0 - (abs(zscore) / self.exit_threshold)
        
        # Entry signals: open position when spread deviates
        elif not position_open:
            if zscore < -self.entry_threshold:
                # Spread too narrow: asset1 undervalued
                signal = Signal.BUY
                confidence = (abs(zscore) - self.entry_threshold) / self.entry_threshold
            
            elif zscore > self.entry_threshold:
                # Spread too wide: asset1 overvalued
                signal = Signal.SELL
                confidence = (abs(zscore) - self.entry_threshold) / self.entry_threshold
        
        return {
            'signal': signal,
            'zscore': zscore,
            'confidence': min(confidence, 1.0)  # Cap at 1.0
        }
    
    def generate_signals_batch(self, zscores, positions=None):
        """
        Generate signals for multiple time periods.
        
        Args:
            zscores: Array/list of Z-scores
            positions: Array/list of current positions (optional)
            
        Returns:
            List of signal dicts
        """
        signals = []
        
        for i, zscore in enumerate(zscores):
            position = positions[i] if positions else None
            signal = self.generate_signal(zscore, position)
            signals.append(signal)
        
        return signals
    
    def should_enter(self, zscore):
        """Check if signal indicates entry."""
        return abs(zscore) > self.entry_threshold
    
    def should_exit(self, zscore):
        """Check if signal indicates exit."""
        return abs(zscore) < self.exit_threshold
    
    def get_signal_direction(self, zscore):
        """
        Get trade direction based on Z-score.
        
        Args:
            zscore: Z-score value
            
        Returns:
            'LONG', 'SHORT', or None
        """
        if zscore < -self.entry_threshold:
            return 'LONG'   # Long asset1, short asset2
        elif zscore > self.entry_threshold:
            return 'SHORT'  # Short asset1, long asset2
        else:
            return None
    
    def update_thresholds(self, entry_threshold=None, exit_threshold=None):
        """
        Update signal thresholds dynamically.
        
        Args:
            entry_threshold: New entry threshold
            exit_threshold: New exit threshold
        """
        if entry_threshold:
            self.entry_threshold = entry_threshold
            logger.info(f"Updated entry threshold to {entry_threshold}")
        
        if exit_threshold:
            self.exit_threshold = exit_threshold
            logger.info(f"Updated exit threshold to {exit_threshold}")