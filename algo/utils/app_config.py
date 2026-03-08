from __future__ import annotations
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


def _convert_value(value_str: Optional[str]) -> Any:
    """Convert XML text to int/float/bool/None or leave as string."""
    if value_str is None:
        return None
    value_str = value_str.strip()
    if not value_str:
        return None
    low = value_str.lower()
    if low in ('true', 'false'):
        return low == 'true'
    if '.' not in value_str:
        try:
            return int(value_str)
        except ValueError:
            pass
    try:
        return float(value_str)
    except ValueError:
        pass
    return value_str


@dataclass
class AppConfig:
    db_dir: Optional[str] = None
    db_file: Optional[str] = None
    symbol: Optional[str] = None
    underlying: Optional[str] = None
    segment: Optional[str] = None
    instrument_type: Optional[str] = None
    exchange: Optional[str] = None
    strategy_type: str = 'ema'
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    data_mode: str = 'historical'
    initialization_periods: int = 50
    live: bool = False
    trades_csv: str = 'trading_journal.csv'
    expiry_index: int = 0
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    start_time: str = "09:15"
    end_time: str = "15:00"
    use_multi_db: bool = False
    preprocessing_days: int = 3
    export_csv: Optional[str] = None
    pl_percent: float = 0.5
    candle_freq: str = '1min'
    tv_autoupdate: bool = False
    tv_update_every: int = 5
    tv_refresh_seconds: int = 0
    tv_auto_open: bool = False
    tv_pl_padding: int = 2
    tv_pl_multiline: bool = False
    tv_pl_color_scale: bool = True
    show_pl_line: bool = True
    pl_line_hover_only: bool = False
    tv_volume_ratio: float = 0.25
    tv_pl_separate_panel: bool = False
    volume_mode: str = 'tick_count'
    chart_library: Optional[str] = None
    additional_indicators: Optional[List[Dict[str, Any]]] = None

    @classmethod
    def from_xml(cls, xml_path: str = "config.xml") -> "AppConfig":
        tree = ET.parse(xml_path)
        root = tree.getroot()
        config_dict: Dict[str, Any] = {}

        for elem in root:
            if elem.tag == 'strategy':
                for subelem in elem:
                    if subelem.tag == 'strategy_name':
                        config_dict['strategy_type'] = _convert_value(subelem.text)
                    elif subelem.tag == 'strategy_params':
                        strategy_params: Dict[str, Any] = {}
                        for param in subelem:
                            if param.tag == 'additional_indicators':
                                indicators: List[Dict[str, Any]] = []
                                for ind_elem in param:
                                    if ind_elem.tag in ('indicator', 'multi_indicator'):
                                        ind_dict: Dict[str, Any] = {'type': ind_elem.tag, 'name': None, 'params': {}}
                                        for sub in ind_elem:
                                            if sub.tag == 'name':
                                                ind_dict['name'] = _convert_value(sub.text)
                                            elif sub.tag == 'params':
                                                params: List[Dict[str, Any]] = []
                                                for p in sub:
                                                    if p.tag == 'param':
                                                        param_dict: Dict[str, Any] = {}
                                                        for subp in p:
                                                            param_dict[subp.tag] = _convert_value(subp.text)
                                                        params.append(param_dict)
                                                ind_dict['params'] = params
                                        indicators.append(ind_dict)
                                strategy_params['additional_indicators'] = indicators
                            else:
                                strategy_params[param.tag] = _convert_value(param.text)
                        config_dict['strategy_params'] = strategy_params
            else:
                config_dict[elem.tag] = _convert_value(elem.text)

        if 'strategy_params' in config_dict and 'additional_indicators' in config_dict['strategy_params']:
            config_dict['additional_indicators'] = config_dict['strategy_params']['additional_indicators']

        symbol = config_dict.get('symbol')
        if symbol:
            config_dict['trades_csv'] = config_dict['trades_csv'].replace('SYMBOL', symbol)
            config_dict['export_csv'] = config_dict['export_csv'].replace('SYMBOL', symbol)

        return cls(**config_dict)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "AppConfig":
        """Construct AppConfig directly from a dictionary."""
        # copy to avoid mutating caller
        data = dict(config_dict)
        symbol = data.get('symbol')
        if symbol:
            if 'trades_csv' in data:
                data['trades_csv'] = data['trades_csv'].replace('SYMBOL', symbol)
            if 'export_csv' in data:
                data['export_csv'] = data['export_csv'].replace('SYMBOL', symbol)
        return cls(**data)

    @classmethod
    def from_json(cls, json_path: str) -> "AppConfig":
        import json
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "AppConfig":
        try:
            import yaml
        except ImportError:
            raise RuntimeError("PyYAML is required to load YAML configuration")
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

