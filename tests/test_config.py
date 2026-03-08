import os
import json
import tempfile
from algo.utils.app_config import AppConfig
from algo.strategy.orb.orb_config import OrbConfig


def test_appconfig_defaults():
    cfg = AppConfig()
    assert cfg.strategy_type == 'ema'
    assert cfg.tv_auto_open is False
    assert isinstance(cfg.strategy_params, dict)


def test_appconfig_from_dict_and_json(tmp_path):
    data = {'symbol': 'TEST', 'trades_csv': 'out/SYMBOL.csv', 'export_csv': 'out/SYMBOL.html'}
    cfg = AppConfig.from_dict(data)
    assert cfg.symbol == 'TEST'
    assert 'TEST' in cfg.trades_csv
    # json round-trip
    p = tmp_path / 'cfg.json'
    p.write_text(json.dumps(data))
    cfg2 = AppConfig.from_json(str(p))
    assert cfg2.symbol == 'TEST'


def test_appconfig_from_xml(tmp_path):
    xml = '''<?xml version="1.0"?>
<config>
  <symbol>XYZ</symbol>
  <trades_csv>out/SYMBOL.csv</trades_csv>
  <export_csv>out/SYMBOL.html</export_csv>
  <strategy>
    <strategy_name>ORB</strategy_name>
    <strategy_params>
      <range_minutes>20</range_minutes>
    </strategy_params>
  </strategy>
</config>
'''
    path = tmp_path / 'cfg.xml'
    path.write_text(xml)
    cfg = AppConfig.from_xml(str(path))
    assert cfg.symbol == 'XYZ'
    assert cfg.strategy_type == 'ORB'
    assert cfg.strategy_params['range_minutes'] == 20


def test_orbconfig_defaults_and_from_appconfig():
    orb = OrbConfig()
    assert orb.range_minutes == 15
    # from AppConfig
    app = AppConfig(strategy_params={'range_minutes': 45})
    orb2 = OrbConfig.from_app_config(app)
    assert orb2.range_minutes == 45
