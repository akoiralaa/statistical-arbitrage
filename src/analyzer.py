import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    """Analyze backtest results and calculate performance metrics."""
    
    def __init__(self, risk_free_rate=0.02):
        """
        Initialize analyzer.
        
        Args:
            risk_free_rate: Annual risk-free rate for Sharpe calculation (default 2%)
        """
        self.risk_free_rate = risk_free_rate
    
    def analyze_backtest(self, backtest_results, starting_capital):
        """
        Comprehensive backtest analysis.
        
        Args:
            backtest_results: Dict from backtester.get_results()
            starting_capital: Initial capital
            
        Returns:
            dict with comprehensive metrics
        """
        trades = backtest_results['trades']
        equity_curve = backtest_results['equity_curve']
        
        if len(trades) == 0:
            logger.warning("No trades to analyze")
            return self._empty_metrics()
        
        # Calculate all metrics
        metrics = {
            # Trade metrics
            **self._calculate_trade_metrics(trades),
            
            # Equity metrics
            **self._calculate_equity_metrics(equity_curve, starting_capital),
            
            # Risk metrics
            **self._calculate_risk_metrics(equity_curve),
            
            # Returns metrics
            **self._calculate_return_metrics(equity_curve, starting_capital),
        }
        
        # Calculate composite ratios
        metrics['sharpe_ratio'] = self._calculate_sharpe_ratio(
            equity_curve, 
            self.risk_free_rate
        )
        metrics['calmar_ratio'] = self._calculate_calmar_ratio(
            metrics['annualized_return'],
            metrics['max_drawdown_pct']
        )
        metrics['profit_factor'] = self._calculate_profit_factor(trades)
        
        return metrics
    
    def _calculate_trade_metrics(self, trades):
        """Calculate trade-based metrics."""
        pnl_list = [t['net_pnl'] for t in trades if t['net_pnl'] is not None]
        
        if len(pnl_list) == 0:
            return {'total_trades': 0}
        
        winning_trades = [p for p in pnl_list if p > 0]
        losing_trades = [p for p in pnl_list if p < 0]
        
        return {
            'total_trades': len(pnl_list),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(pnl_list),
            'loss_rate': len(losing_trades) / len(pnl_list),
            'total_pnl': sum(pnl_list),
            'avg_pnl_per_trade': np.mean(pnl_list),
            'largest_win': max(pnl_list) if winning_trades else 0,
            'largest_loss': min(pnl_list) if losing_trades else 0,
            'avg_win': np.mean(winning_trades) if winning_trades else 0,
            'avg_loss': abs(np.mean(losing_trades)) if losing_trades else 0,
            'consecutive_wins': self._calculate_consecutive_wins(pnl_list),
            'consecutive_losses': self._calculate_consecutive_losses(pnl_list),
        }
    
    def _calculate_equity_metrics(self, equity_curve, starting_capital):
        """Calculate equity curve metrics."""
        if equity_curve is None or len(equity_curve) == 0:
            return {}
        
        final_capital = equity_curve['capital'].iloc[-1]
        
        return {
            'starting_capital': starting_capital,
            'final_capital': final_capital,
            'total_return': (final_capital - starting_capital) / starting_capital,
            'total_return_pct': ((final_capital - starting_capital) / starting_capital) * 100,
        }
    
    def _calculate_return_metrics(self, equity_curve, starting_capital):
        """Calculate return-based metrics."""
        if equity_curve is None or len(equity_curve) < 2:
            return {}
        
        capital = equity_curve['capital'].values
        returns = np.diff(capital) / capital[:-1]
        
        num_days = len(equity_curve)
        num_years = num_days / 252
        
        total_return = (capital[-1] - capital[0]) / capital[0]
        annualized_return = (1 + total_return) ** (1 / num_years) - 1 if num_years > 0 else 0
        
        return {
            'annualized_return': annualized_return,
            'annualized_return_pct': annualized_return * 100,
            'daily_avg_return': np.mean(returns),
            'daily_std_return': np.std(returns),
        }
    
    def _calculate_risk_metrics(self, equity_curve):
        """Calculate risk metrics."""
        if equity_curve is None or len(equity_curve) == 0:
            return {}
        
        capital = equity_curve['capital'].values
        
        # Maximum drawdown
        running_max = np.maximum.accumulate(capital)
        drawdowns = (capital - running_max) / running_max
        max_dd = np.min(drawdowns)
        max_dd_pct = abs(max_dd) * 100
        
        # Volatility
        returns = np.diff(capital) / capital[:-1]
        daily_volatility = np.std(returns)
        annual_volatility = daily_volatility * np.sqrt(252)
        
        return {
            'max_drawdown': max_dd,
            'max_drawdown_pct': max_dd_pct,
            'daily_volatility': daily_volatility,
            'annual_volatility': annual_volatility,
        }
    
    def _calculate_sharpe_ratio(self, equity_curve, risk_free_rate):
        """
        Calculate Sharpe Ratio.
        
        Sharpe = (annual_return - risk_free_rate) / annual_volatility
        """
        if equity_curve is None or len(equity_curve) < 2:
            return 0
        
        capital = equity_curve['capital'].values
        returns = np.diff(capital) / capital[:-1]
        
        # Annualize
        daily_return = np.mean(returns)
        annual_return = daily_return * 252
        
        daily_volatility = np.std(returns)
        annual_volatility = daily_volatility * np.sqrt(252)
        
        if annual_volatility == 0:
            return 0
        
        sharpe = (annual_return - risk_free_rate) / annual_volatility
        return sharpe
    
    def _calculate_calmar_ratio(self, annual_return, max_drawdown_pct):
        """
        Calculate Calmar Ratio.
        
        Calmar = annual_return / max_drawdown
        """
        if max_drawdown_pct == 0 or max_drawdown_pct is None:
            return 0
        
        calmar = annual_return / (max_drawdown_pct / 100)
        return calmar
    
    def _calculate_profit_factor(self, trades):
        """
        Calculate Profit Factor.
        
        Profit Factor = gross_profit / gross_loss
        """
        gross_profit = sum([t['net_pnl'] for t in trades if t['net_pnl'] > 0])
        gross_loss = abs(sum([t['net_pnl'] for t in trades if t['net_pnl'] < 0]))
        
        if gross_loss == 0:
            return gross_profit / 0.01 if gross_profit > 0 else 0
        
        return gross_profit / gross_loss
    
    def _calculate_consecutive_wins(self, pnl_list):
        """Calculate maximum consecutive winning trades."""
        max_consecutive = 0
        current_consecutive = 0
        
        for pnl in pnl_list:
            if pnl > 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def _calculate_consecutive_losses(self, pnl_list):
        """Calculate maximum consecutive losing trades."""
        max_consecutive = 0
        current_consecutive = 0
        
        for pnl in pnl_list:
            if pnl < 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def _empty_metrics(self):
        """Return empty metrics dict."""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'sharpe_ratio': 0,
            'max_drawdown_pct': 0,
            'total_return_pct': 0,
            'annualized_return_pct': 0,
        }
    
    def print_report(self, metrics):
        """Print formatted performance report."""
        report = "\n" + "=" * 70
        report += "\nPERFORMANCE REPORT\n"
        report += "=" * 70
        
        if metrics['total_trades'] == 0:
            report += "\nNo trades executed."
            logger.info(report)
            return
        
        report += f"\n{'TRADE STATISTICS':^70}"
        report += f"\n{'-' * 70}"
        report += f"\nTotal Trades:           {metrics['total_trades']}"
        report += f"\nWinning Trades:         {metrics['winning_trades']} ({metrics['win_rate']*100:.2f}%)"
        report += f"\nLosing Trades:          {metrics['losing_trades']} ({metrics['loss_rate']*100:.2f}%)"
        report += f"\nLargest Win:            ${metrics['largest_win']:,.2f}"
        report += f"\nLargest Loss:           ${metrics['largest_loss']:,.2f}"
        report += f"\nAvg Win:                ${metrics['avg_win']:,.2f}"
        report += f"\nAvg Loss:               ${metrics['avg_loss']:,.2f}"
        report += f"\nProfit Factor:          {metrics['profit_factor']:.2f}"
        
        report += f"\n\n{'RETURNS':^70}"
        report += f"\n{'-' * 70}"
        report += f"\nTotal Return:           {metrics['total_return_pct']:.2f}%"
        report += f"\nAnnualized Return:      {metrics['annualized_return_pct']:.2f}%"
        report += f"\nDaily Avg Return:       {metrics['daily_avg_return']*100:.4f}%"
        
        report += f"\n\n{'RISK METRICS':^70}"
        report += f"\n{'-' * 70}"
        report += f"\nMax Drawdown:           {metrics['max_drawdown_pct']:.2f}%"
        report += f"\nDaily Volatility:       {metrics['daily_volatility']*100:.4f}%"
        report += f"\nAnnual Volatility:      {metrics['annual_volatility']*100:.2f}%"
        report += f"\nSharpe Ratio:           {metrics['sharpe_ratio']:.2f}"
        report += f"\nCalmar Ratio:           {metrics['calmar_ratio']:.2f}"
        
        report += f"\n{'=' * 70}\n"
        
        logger.info(report)