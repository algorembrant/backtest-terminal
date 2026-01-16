import MetaTrader5 as mt5
import json
import os
from datetime import datetime
import pandas as pd

class BacktestBridge:
    """Bridge to run MQL5 Expert Advisors and extract backtest results"""
    
    def __init__(self):
        self.mt5_path = None
        
    def init_mt5(self):
        """Initialize MT5 connection"""
        if not mt5.initialize():
            print(f"MT5 initialization failed: {mt5.last_error()}")
            return False
        
        # Get MT5 terminal path
        terminal_info = mt5.terminal_info()
        self.mt5_path = terminal_info.path
        print(f"MT5 Path: {self.mt5_path}")
        return True
    
    def compile_ea(self, mq5_file_path):
        """
        Compile MQL5 Expert Advisor
        Note: This requires MetaEditor CLI or manual compilation
        """
        # Check if file exists
        if not os.path.exists(mq5_file_path):
            return {'success': False, 'error': 'MQ5 file not found'}
        
        # For now, assume EA is already compiled
        # You need to manually compile in MetaEditor or use MetaEditor CLI
        ex5_path = mq5_file_path.replace('.mq5', '.ex5')
        
        if not os.path.exists(ex5_path):
            return {
                'success': False, 
                'error': 'EX5 file not found. Please compile in MetaEditor first.'
            }
        
        return {'success': True, 'ex5_path': ex5_path}
    
    def get_history_deals(self, from_date, to_date):
        """Get historical deals from MT5"""
        deals = mt5.history_deals_get(from_date, to_date)
        
        if deals is None:
            return []
        
        deals_list = []
        for deal in deals:
            deals_list.append({
                'ticket': deal.ticket,
                'order': deal.order,
                'time': deal.time,
                'type': 'BUY' if deal.type == 0 else 'SELL',
                'entry': 'IN' if deal.entry == 0 else 'OUT',
                'symbol': deal.symbol,
                'volume': deal.volume,
                'price': deal.price,
                'profit': deal.profit,
                'commission': deal.commission,
                'swap': deal.swap,
                'comment': deal.comment
            })
        
        return deals_list
    
    def get_history_orders(self, from_date, to_date):
        """Get historical orders from MT5"""
        orders = mt5.history_orders_get(from_date, to_date)
        
        if orders is None:
            return []
        
        orders_list = []
        for order in orders:
            orders_list.append({
                'ticket': order.ticket,
                'time_setup': order.time_setup,
                'time_done': order.time_done,
                'type': order.type,
                'state': order.state,
                'symbol': order.symbol,
                'volume_initial': order.volume_initial,
                'volume_current': order.volume_current,
                'price_open': order.price_open,
                'price_current': order.price_current,
                'sl': order.sl,
                'tp': order.tp,
                'comment': order.comment
            })
        
        return orders_list
    
    def analyze_backtest_results(self, from_date, to_date):
        """Analyze backtest results and calculate statistics"""
        deals = self.get_history_deals(from_date, to_date)
        
        if not deals:
            return {'error': 'No deals found in the specified period'}
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(deals)
        
        # Calculate statistics
        total_trades = len(df[df['entry'] == 'OUT'])
        winning_trades = len(df[(df['entry'] == 'OUT') & (df['profit'] > 0)])
        losing_trades = len(df[(df['entry'] == 'OUT') & (df['profit'] < 0)])
        
        total_profit = df[df['entry'] == 'OUT']['profit'].sum()
        total_commission = df[df['entry'] == 'OUT']['commission'].sum()
        total_swap = df[df['entry'] == 'OUT']['swap'].sum()
        
        net_profit = total_profit + total_commission + total_swap
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Calculate max drawdown
        df_out = df[df['entry'] == 'OUT'].copy()
        df_out['cumulative_profit'] = df_out['profit'].cumsum()
        df_out['peak'] = df_out['cumulative_profit'].cummax()
        df_out['drawdown'] = df_out['peak'] - df_out['cumulative_profit']
        max_drawdown = df_out['drawdown'].max()
        
        # Profit factor
        gross_profit = df[(df['entry'] == 'OUT') & (df['profit'] > 0)]['profit'].sum()
        gross_loss = abs(df[(df['entry'] == 'OUT') & (df['profit'] < 0)]['profit'].sum())
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': round(win_rate, 2),
            'total_profit': round(total_profit, 2),
            'total_commission': round(total_commission, 2),
            'total_swap': round(total_swap, 2),
            'net_profit': round(net_profit, 2),
            'max_drawdown': round(max_drawdown, 2),
            'profit_factor': round(profit_factor, 2),
            'gross_profit': round(gross_profit, 2),
            'gross_loss': round(gross_loss, 2),
            'deals': deals
        }
    
    def export_backtest_report(self, from_date, to_date, output_file='backtest_report.json'):
        """Export backtest results to JSON file"""
        results = self.analyze_backtest_results(from_date, to_date)
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"Backtest report exported to {output_file}")
        return results

# Example usage
if __name__ == "__main__":
    bridge = BacktestBridge()
    
    if bridge.init_mt5():
        # Define backtest period
        from_date = datetime(2024, 1, 1)
        to_date = datetime.now()
        
        # Analyze results
        results = bridge.analyze_backtest_results(from_date, to_date)
        
        print("\n=== BACKTEST RESULTS ===")
        print(f"Total Trades: {results.get('total_trades', 0)}")
        print(f"Win Rate: {results.get('win_rate', 0)}%")
        print(f"Net Profit: ${results.get('net_profit', 0)}")
        print(f"Max Drawdown: ${results.get('max_drawdown', 0)}")
        print(f"Profit Factor: {results.get('profit_factor', 0)}")
        
        # Export to JSON
        bridge.export_backtest_report(from_date, to_date)
        
        mt5.shutdown()