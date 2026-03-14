from nslogger.option_chain_manager import OptionChainManager
from nslogger.history_data_manager import HistoryDataManager
import os
import pandas as pd

class DataManager:
    def __init__(self, symbol, db_dir, db_file, multi=False):
        self.multi = multi
        self.symbol = symbol
        self.db_dir = db_dir
        self.db_file = db_file
        
        if self.multi and self.symbol:
            self.db_files = [f for f in os.listdir(self.db_dir) if f.endswith('.db') and self.symbol.lower() in f.lower()]
        else:
            self.db_files = [self.db_file] if self.db_file else []
        
        self.managers = []
        for db_f in self.db_files:
            db_path = os.path.join(self.db_dir, db_f)
            self.managers.append({
                'option': OptionChainManager(db_f, db_path),
                'history': HistoryDataManager(db_f, db_path)
            })
    
    # returns a dataframe with live stock data
    def get_live_stock_data(self, symbol):
        dfs = []
        for m in self.managers:
            df = m['history'].sql.get_live_data(symbol)
            if not df.empty:
                dfs.append(df)
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    
    def get_live_option_chain(self, symbol, expiry_index):
        if self.managers:
            m = self.managers[0]
            expiry = m['option'].get_expiry_by_index(symbol, expiry_index)
            return m['option'].get_live_option_chain_by_expiry(expiry[1] if expiry else None)
        return None
    
    # returns a dataframe with historical data
    def get_historical_data(self, symbol, start_date, end_date):
        dfs = []
        for m in self.managers:
            df = m['history'].get_historical_data(symbol, start_date, end_date)
            if not df.empty:
                dfs.append(df)
        combined = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
        if not combined.empty:
            combined = combined.sort_values('timestamp').drop_duplicates(subset='timestamp')
        return combined
    
    def prepare_data_for_strategy(self, islive: bool = False):
        # Placeholder for any data preprocessing steps needed before feeding into strategy
        df = self.get_live_stock_data(self.symbol) if islive else self.get_historical_data(self.symbol, None, None)
        return df
    
    