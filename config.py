import json
import os
from typing import Any, Dict, Optional
from pathlib import Path


class Config:
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "config.json")
        self.config_path = config_path
        self._config: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        except FileNotFoundError:
            raise ConfigError(f"Configuration file not found: {self.config_path}")
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in configuration file: {e}")

    def save(self) -> None:
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            raise ConfigError(f"Failed to save configuration: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    def get_api_config(self) -> Dict[str, Any]:
        return self._config.get('api', {})

    def get_recognition_config(self) -> Dict[str, Any]:
        return self._config.get('recognition', {})

    def get_cleaning_config(self) -> Dict[str, Any]:
        return self._config.get('cleaning', {})

    def get_output_config(self) -> Dict[str, Any]:
        return self._config.get('output', {})

    def get_logging_config(self) -> Dict[str, Any]:
        return self._config.get('logging', {})

    @property
    def base_url(self) -> str:
        return self.get('api.base_url', 'https://api.openai.com/v1')

    @property
    def api_key(self) -> str:
        return self.get('api.api_key', '')

    @property
    def model(self) -> str:
        return self.get('api.model', 'gpt-3.5-turbo')

    @property
    def temperature(self) -> float:
        return self.get('api.temperature', 0.3)

    @property
    def max_tokens(self) -> int:
        return self.get('api.max_tokens', 2000)

    @property
    def timeout(self) -> int:
        return self.get('api.timeout', 60)


class ConfigError(Exception):
    pass


_config_instance: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    global _config_instance
    if _config_instance is None or config_path is not None:
        _config_instance = Config(config_path)
    return _config_instance


def reset_config() -> None:
    global _config_instance
    _config_instance = None