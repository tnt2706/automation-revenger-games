import json
from pathlib import Path
from typing import Any, Dict, Optional
import os

class Config:
    _config: Dict[str, Any] = {}

    @classmethod
    def load(cls, env: Optional[str] = "dev"):
        """Load configuration from JSON file, env can be overridden"""
     
        env = env or os.environ.get("ENV", "dev")
        config_file = Path(__file__).parent / f"{env}.json"
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")
        with open(config_file, "r", encoding="utf-8") as f:
            print(f"✅ Loaded config for ENV={Config.get('env',env)}")
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

    @classmethod
    def get_template(cls, provider: str) -> str:
        """Get game URL template: 'rec' or 'rev'"""

        return cls.get("game", "urlTemplates", provider)

    @classmethod
    def get_game_url(cls, game_code: str, provider: str, oc: str, token: str, language: str) -> str:
        """Generate the full game URL"""
        template = cls.get_template(provider)
        return template.format(gameCode=game_code, oc=oc, token=token, language=language)
