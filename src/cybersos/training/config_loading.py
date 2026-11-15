import math
from dataclasses import fields
from pathlib import Path
from typing import TypeVar

from cybersos.project_paths import PROJECT_ROOT
from cybersos.serialization import load_strict_yaml


ConfigType = TypeVar('ConfigType')


def load_typed_config(path: str | Path, config_type: type[ConfigType]) -> ConfigType:
    values = load_strict_yaml(path)
    if not isinstance(values, dict):
        raise ValueError('Training configuration must be a mapping')
    allowed = {field.name for field in fields(config_type)}
    if unknown := set(values) - allowed:
        raise ValueError(f'Unknown configuration fields: {sorted(unknown)}')
    return config_type(**values)


def project_path(value: str) -> Path:
    """Configured paths are relative to the project, never to the working directory."""
    return PROJECT_ROOT / value


def positive_integer(name: str, value: int) -> None:
    if type(value) is not int or value < 1:
        raise ValueError(f'{name} must be a positive integer')


def positive_rate(name: str, value: float) -> None:
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be finite and positive')


def require_string(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} must be a nonempty string')
