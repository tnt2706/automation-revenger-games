import json
from pathlib import Path
from typing import Any, Dict, Optional
import os


class Config:
    _config: Dict[str, Any] = {}

    @classmethod
    def load(cls, env: Optional[str] = None):
        """Load configuration from JSON file, env can be overridden"""

        env = env or os.environ.get("ENV", "dev")
        config_file = Path(__file__).parent / f"{env}.json"
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")
        with open(config_file, "r", encoding="utf-8") as f:
            cls._config = json.load(f)

    @classmethod
    def get(cls, *keys, default=None) -> Any:
        """Retrieve a value from the config, e.g., Config.get('game','operatorTarget')"""

        cfg = cls._config
        for key in keys:
            if not isinstance(cfg, dict):
                return default
            cfg = cfg.get(key, default)
        return cfg
