import os
from algo.engine.controller import Controller
from algo.utils.app_config import AppConfig


def main():
    config = AppConfig.from_xml("config.xml")
    config.db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), config.db_dir))
    symbol_info = { "symbol": config.symbol, "instrument_type": config.instrument_type }
    controller = Controller(symbol_info, config)
    controller.run()


if __name__ == "__main__":
    main()
