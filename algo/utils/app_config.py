import xml.etree.ElementTree as ET
import os
from typing import List, Dict, Any

class AppConfig:
    def __init__(self, config_path: str = None, **kwargs):
        # Determine config path based on __file__ location if not provided
        if config_path is None:
            # Go up 3 directories from this file to reach the root where config.xml is
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.xml')
        
        self.config_path = config_path
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
            volume_mode='tick_count' # how to derive volume: tick_count | price_range | abs_return | real
            # session_close_time removed: strategy now responsible for EOD logic
        )
        for k, v in default_cfg.items():
            setattr(self, k, kwargs.get(k, v))
    
    @classmethod
    def from_xml(cls, xml_path: str = None):
        """Load configuration from XML file. If xml_path is None, uses default location based on __file__"""
        if xml_path is None:
            xml_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.xml')
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
                            strategy_params[param.tag] = convert_value(param.text)
                        config_dict['strategy_params'] = strategy_params
            else:
                config_dict[elem.tag] = convert_value(elem.text)
        
        return cls(config_path=xml_path, **config_dict)
    
    def load_chart_indicators(self) -> List[Dict[str, Any]]:
        """Load chart indicators from NSChart section in config.xml"""
        tree = ET.parse(self.config_path)
        root = tree.getroot()
        
        indicators = []
        nschart = root.find('NSChart')
        if nschart is not None:
            indicators_elem = nschart.find('Indicators')
            if indicators_elem is not None:
                for ind_elem in indicators_elem.findall('Indicator'):
                    name = ind_elem.find('Name')
                    value = ind_elem.find('Value')
                    type_ = ind_elem.find('Type')
                    color = ind_elem.find('Color')
                    linewidth = ind_elem.find('LineWidth')
                    run_on_candle = ind_elem.find('RunOnCandle')
                    visible = ind_elem.find('Visible')
                    
                    indicator_dict = {
                        'name': name.text.strip() if name is not None and name.text else None,
                        'value': int(value.text.strip()) if value is not None and value.text else None,
                        'type': type_.text.strip() if type_ is not None and type_.text else 'line',
                        'color': color.text.strip() if color is not None and color.text else '#FF0000',
                        'linewidth': int(linewidth.text.strip()) if linewidth is not None and linewidth.text else 1,
                        'run_on_candle': run_on_candle.text.strip() if run_on_candle is not None and run_on_candle.text else 'close',
                        'visible': visible.text.strip().lower() == 'true' if visible is not None and visible.text else True
                    }
                    indicators.append(indicator_dict)
        
        return indicators
