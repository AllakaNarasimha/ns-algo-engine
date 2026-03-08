import pandas as pd
from algo.engine.data_state_manager import DataStateManager
from algo.engine.trade_manager import TradeManager
from typing import Dict, Any
from algo.utils.app_config import AppConfig
from algo.utils.data_manager import DataManager
from algo.utils.trade_journal import TradeJournal
from algo.utils.ns_tvchart import TvChart

class Controller:
    def __init__(self, symbol_info: Dict[str, Any], app_config: AppConfig):
        self.symbol = symbol_info['symbol']
        self.symbol_instrument_type = symbol_info['instrument_type']
        self.app_config = app_config
        self.data_manager = DataManager(self.symbol, app_config.db_dir, app_config.db_file, multi=False)
        self.tv_chart = TvChart(self.symbol, app_config)

    def run(self) -> None:
        """Main control logic for the algorithmic trading engine."""
        symbol_ticker = f'{self.app_config.exchange}:{self.symbol}-{self.symbol_instrument_type}'
        if self.app_config.live:
            data = self.data_manager.get_live_stock_data(symbol_ticker)
        else:
            data = self.data_manager.get_historical_data(
                symbol_ticker, self.app_config.start_date, self.app_config.end_date)
        
        # Pre-process data
        data.set_index('timestamp', inplace=True)
        data.index = pd.to_datetime(data.index, unit='s', utc=True).tz_convert('Asia/Kolkata')
        data = data.sort_index()
        # Filter by trading hours
        data = data.between_time(self.app_config.start_time, self.app_config.end_time)
        
        # Initialize components
        data_state_manager = DataStateManager()
        trade_manager = TradeManager(self.app_config)
        trade_journal = TradeJournal(self.symbol, self.app_config)
        self.tv_chart.write_placeholder()
        
        # Initialize strategy
        if self.app_config.strategy_type == 'ORB':
            from algo.strategy.orb.orb_strategy import ORBStrategy
            self.strategy = ORBStrategy(self.app_config, data_state_manager)
        else:
            self.strategy = None

        # Add strategy-specific columns
        strategy_columns = ['orb_time', 'pivot_time', 'pivot_high', 'pivot_low', 
                          'pivot_direction', 'range_high', 'range_low']
        for col in strategy_columns:
            dtype = 'float64' if any(x in col for x in ['high', 'low', 'range']) else 'object'
            data[col] = pd.Series(dtype=dtype)
            
        ltp_column_name = 'ltp' if 'ltp' in data.columns and data['ltp'].notnull().all() else 'close'
                
        # Main processing loop
        while True:
            record = data_state_manager.get_latest_record(data)
            if record is None:
                break
            if self.strategy:
                trade_signal = self.strategy.update(record, record['timestamp'])
                trade_data = trade_manager.process_signal(record, trade_signal)
                if trade_data is None:
                    continue
                trade_journal.update_trade_data(record['timestamp'], record[ltp_column_name], trade_data)
                try:
                    self.strategy.candles_df.set_index('timestamp', inplace=True)
                    self.tv_chart.maybe_export(
                        self.strategy.candles_df.iloc[:data_state_manager.current_index], 
                        trade_journal.trades
                    )
                except Exception:
                    pass
        
        # Final export
        if self.tv_chart and self.strategy:
            try:
                df_chart = self.strategy.candles_df.copy()
                df_chart.index = pd.to_datetime(df_chart.index, unit='s', utc=True).tz_convert('Asia/Kolkata')
                df_chart = df_chart.sort_index()
                self.tv_chart.export_final(df_chart, trade_journal.trades)
            except Exception:
                pass


 