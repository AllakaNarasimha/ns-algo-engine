# Configuration

The engine uses an `AppConfig` dataclass to hold all settings. Configuration can be loaded in several ways:

* **XML** (legacy):
  ```python
  from algo.utils.app_config import AppConfig
  cfg = AppConfig.from_xml('config.xml')
  ```
  `config.xml` should follow the structure previously used by the project. The loader
  converts values to the appropriate Python type automatically.

* **Dictionary**: pass a plain `dict` of values:
  ```python
  cfg = AppConfig.from_dict({
      'symbol': 'XYZ',
      'strategy_type': 'ORB',
      'strategy_params': {'range_minutes': 20}
  })
  ```

* **JSON** or **YAML** file:
  ```python
  cfg = AppConfig.from_json('config.json')
  cfg = AppConfig.from_yaml('config.yaml')  # requires PyYAML
  ```

The `OrbConfig` helper also accepts an `AppConfig` instance:

```python
from algo.strategy.orb.orb_config import OrbConfig
orb_cfg = OrbConfig.from_app_config(cfg)
```

All configuration fields are type annotated and have sensible defaults. The
`AppConfig` dataclass is used throughout the codebase for better static analysis and
IDE support.
