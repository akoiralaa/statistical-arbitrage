import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller
from scipy import stats
import logging

logger = logging.getLogger(__name__)

class CointegrationTester:
    """Test if two price series are cointegrated and calculate trading parameters."""
    
    def __init__(self, min_pvalue=0.05):
        """
        Initialize cointegration tester.
        
        Args:
            min_pvalue: Maximum p-value to consider series cointegrated (default 0.05)
        """
        self.min_pvalue = min_pvalue
    
    def calculate_hedge_ratio(self, price1, price2):
        """
        Calculate hedge ratio using OLS regression.
        
        The hedge ratio tells us how many units of asset2 to short 
        per 1 unit of asset1 to create a market-neutral spread.
        
        spread = price1 - (hedge_ratio * price2)
        
        Args:
            price1: Array of prices for asset 1
            price2: Array of prices for asset 2
            
        Returns:
            float: Hedge ratio coefficient
        """
        # Add constant for regression
        X = np.column_stack([np.ones(len(price2)), price2])
        
        # OLS: price1 = intercept + hedge_ratio * price2 + residual
        # We use np.linalg.lstsq to solve: X @ beta = price1
        beta, _, _, _ = np.linalg.lstsq(X, price1, rcond=None)
        
        # beta[0] is intercept, beta[1] is hedge ratio
        hedge_ratio = beta[1]
        
        return hedge_ratio
    
    def calculate_spread(self, price1, price2, hedge_ratio):
        """
        Calculate the spread between two cointegrated series.
        
        Args:
            price1: Price of asset 1
            price2: Price of asset 2
            hedge_ratio: Calculated hedge ratio
            
        Returns:
            float or array: Spread value(s)
        """
        return price1 - (hedge_ratio * price2)
    
    def adf_test(self, series, maxlag=None):
        """
        Augmented Dickey-Fuller test for stationarity.
        
        H0: Series has a unit root (non-stationary)
        H1: Series is stationary
        
        If p-value < 0.05, we reject H0 and conclude series is stationary.
        
        Args:
            series: Time series to test
            maxlag: Maximum number of lags to test (None = auto)
            
        Returns:
            dict with test results
        """
        try:
            result = adfuller(series, maxlag=maxlag, regression='c')
            
            return {
                'adf_statistic': result[0],
                'pvalue': result[1],
                'usedlag': result[2],
                'nobs': result[3],
                'critical_values': result[4],
                'ic_best': result[5]
            }
        except Exception as e:
            logger.error(f"ADF test failed: {e}")
            return None
    
    def test_cointegration(self, price1, price2, lookback=252):
        """
        Test if two price series are cointegrated.
        
        Steps:
        1. Calculate hedge ratio using OLS
        2. Calculate spread
        3. Run ADF test on spread
        4. If ADF p-value < threshold, series are cointegrated
        
        Args:
            price1: Array/Series of prices for asset 1
            price2: Array/Series of prices for asset 2
            lookback: Number of periods to use for testing (default 252 = 1 year)
            
        Returns:
            dict with cointegration test results
        """
        # Use only recent data for lookback
        if len(price1) > lookback:
            price1_test = price1[-lookback:]
            price2_test = price2[-lookback:]
        else:
            price1_test = price1
            price2_test = price2
        
        # Calculate hedge ratio
        hedge_ratio = self.calculate_hedge_ratio(price1_test, price2_test)
        
        # Calculate spread
        spread = self.calculate_spread(price1_test, price2_test, hedge_ratio)
        
        # Run ADF test on spread
        adf_result = self.adf_test(spread)
        
        if adf_result is None:
            return {
                'cointegrated': False,
                'adf_pvalue': None,
                'hedge_ratio': hedge_ratio,
                'spread_mean': None,
                'spread_std': None,
                'error': 'ADF test failed'
            }
        
        # Check if cointegrated
        is_cointegrated = adf_result['pvalue'] < self.min_pvalue
        
        # Calculate spread statistics
        spread_mean = np.mean(spread)
        spread_std = np.std(spread)
        
        result = {
            'cointegrated': is_cointegrated,
            'adf_pvalue': adf_result['pvalue'],
            'adf_statistic': adf_result['adf_statistic'],
            'hedge_ratio': hedge_ratio,
            'spread_mean': spread_mean,
            'spread_std': spread_std,
            'lookback_periods': len(price1_test),
            'critical_values': adf_result['critical_values']
        }
        
        return result
    
    def test_multiple_pairs(self, price_data, pairs, lookback=252):
        """
        Test cointegration for multiple pairs.
        
        Args:
            price_data: Dict of {pair: DataFrame} with 'close' column
            pairs: List of tuples (asset1, asset2) to test
            lookback: Lookback period
            
        Returns:
            Dict of {pair_tuple: cointegration_result}
        """
        results = {}
        
        for pair1, pair2 in pairs:
            if pair1 not in price_data or pair2 not in price_data:
                logger.warning(f"Missing data for pair ({pair1}, {pair2})")
                continue
            
            price1 = price_data[pair1]['close'].values
            price2 = price_data[pair2]['close'].values
            
            # Ensure same length
            min_len = min(len(price1), len(price2))
            price1 = price1[-min_len:]
            price2 = price2[-min_len:]
            
            result = self.test_cointegration(price1, price2, lookback)
            results[(pair1, pair2)] = result
            
            # Log result
            if result['cointegrated']:
                logger.info(f"✓ {pair1} & {pair2} are COINTEGRATED (p={result['adf_pvalue']:.4f})")
            else:
                logger.info(f"✗ {pair1} & {pair2} NOT cointegrated (p={result['adf_pvalue']:.4f})")
        
        return results
    
    def calculate_zscore(self, current_spread, spread_mean, spread_std):
        """
        Calculate Z-score for current spread.
        
        Z-score = (current_spread - mean) / std
        
        Interpretation:
        - Z-score > 2.0: Spread is 2 std above mean (asset1 overvalued)
        - Z-score < -2.0: Spread is 2 std below mean (asset1 undervalued)
        - Z-score ≈ 0: Spread at equilibrium
        
        Args:
            current_spread: Current spread value
            spread_mean: Historical mean of spread
            spread_std: Historical std of spread
            
        Returns:
            float: Z-score value
        """
        if spread_std == 0:
            logger.warning("Spread std is 0, cannot calculate Z-score")
            return 0
        
        zscore = (current_spread - spread_mean) / spread_std
        return zscore