import xml.etree.ElementTree as ET

class AppConfig:
    def __init__(self, **kwargs):
        default_cfg = dict(
            db_dir=None, db_file=None, symbol=None, underlying=None, segment=None,
            instrument_type=None, exchange=None, strategy_type='ema', strategy_params=None,
            data_mode='historical', initialization_periods=50, live=False,
            trades_csv='trading_journal.csv', expiry_index=0, start_date=None,
            end_date=None, start_time="09:15", end_time="15:00", use_multi_db=False, preprocessing_days=3,
            export_csv=None, pl_percent=0.5, candle_freq='1min',
            tv_autoupdate=False,   # if True, regenerate TV HTML every tv_update_every candles
            tv_update_every=5,     # frequency (in completed candles) for auto export
            tv_refresh_seconds=0,  # if >0, inject meta refresh tag into HTML for auto reload
            tv_auto_open=False,    # if True, open HTML in browser on first export
            tv_pl_padding=2,       # number of "\n" lines to pad P&L marker text to shift vertically
            tv_pl_multiline=False, # if True show each P&L on its own line when multiple trades exit same candle
            tv_pl_color_scale=True, # scale marker color intensity by absolute P&L
            show_pl_line=True,      # plot cumulative P&L line in TV (and MPL) charts
            pl_line_hover_only=False, # if True show PL line only on hover
            tv_volume_ratio=0.25,     # fraction (0.10-0.50) of vertical space for volume pane
            tv_pl_separate_panel=False, # if True render cumulative P&L in its own chart below
            volume_mode='tick_count', # how to derive volume: tick_count | price_range | abs_return | real
            additional_indicators=None
            # session_close_time removed: strategy now responsible for EOD logic
        )
        for k, v in default_cfg.items():
            setattr(self, k, kwargs.get(k, v))
    
    @classmethod
    def from_xml(cls, xml_path):
        """Load configuration from XML file"""
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        config_dict = {}
        
        # Helper function to convert string values to appropriate types
        def convert_value(value_str):
            if value_str is None:
                return None
            value_str = value_str.strip()
            if not value_str:
                return None
            # Boolean conversion
            if value_str.lower() in ('true', 'false'):
                return value_str.lower() == 'true'
            # Try integer conversion
            try:
                if '.' not in value_str:
                    return int(value_str)
            except ValueError:
                pass
            # Try float conversion
            try:
                return float(value_str)
            except ValueError:
                pass
            # Return as string
            return value_str
        
        # Parse all elements
        for elem in root:
            if elem.tag == 'strategy':
                for subelem in elem:
                    if subelem.tag == 'strategy_name':
                        config_dict['strategy_type'] = convert_value(subelem.text)
                    elif subelem.tag == 'strategy_params':
                        # Parse nested strategy parameters
                        strategy_params = {}
                        for param in subelem:
                            if param.tag == 'additional_indicators':
                                indicators = []
                                for ind_elem in param:
                                    if ind_elem.tag in ('indicator', 'multi_indicator'):
                                        ind_dict = {'type': ind_elem.tag, 'name': None, 'params': {}}
                                        for sub in ind_elem:
                                            if sub.tag == 'name':
                                                ind_dict['name'] = convert_value(sub.text)
                                            elif sub.tag == 'params':
                                                params = []
                                                for p in sub:
                                                    if p.tag == 'param':
                                                        param_dict = {}
                                                        for subp in p:
                                                            param_dict[subp.tag] = convert_value(subp.text)
                                                        params.append(param_dict)
                                                ind_dict['params'] = params
                                        indicators.append(ind_dict)
                                strategy_params['additional_indicators'] = indicators
                            else:
                                strategy_params[param.tag] = convert_value(param.text)
                        config_dict['strategy_params'] = strategy_params
            else:
                config_dict[elem.tag] = convert_value(elem.text)
        
        # Set additional_indicators from strategy_params
        if 'strategy_params' in config_dict and 'additional_indicators' in config_dict['strategy_params']:
            config_dict['additional_indicators'] = config_dict['strategy_params']['additional_indicators']
        
        # Update CSV names with symbol
        symbol = config_dict.get('symbol')
        if symbol:
            config_dict['trades_csv'] = config_dict['trades_csv'].replace('SYMBOL', symbol)
            config_dict['export_csv'] = config_dict['export_csv'].replace('SYMBOL', symbol)
        
        return cls(**config_dict)
