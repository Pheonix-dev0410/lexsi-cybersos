from pathlib import Path
from typing import Any

import yaml


class DuplicateYamlKeyError(ValueError):
    pass


class _DuplicateRejectingLoader(yaml.SafeLoader):
    pass


def _unique_mapping(loader: _DuplicateRejectingLoader, node: yaml.MappingNode) -> dict[Any, Any]:
    result: dict[Any, Any] = {}
    for key, value in loader.construct_pairs(node, deep=True):
        if key in result:
            raise DuplicateYamlKeyError(f'Duplicate YAML key: {key}')
        result[key] = value
    return result


_DuplicateRejectingLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def load_strict_yaml(path: str | Path) -> Any:
    """Safe-load YAML, rejecting duplicate keys that PyYAML would otherwise silently overwrite."""
    with Path(path).open() as stream:
        return yaml.load(stream, Loader=_DuplicateRejectingLoader)
