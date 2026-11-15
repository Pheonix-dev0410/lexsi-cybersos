from enum import Enum

import pytest

from cybersos.serialization import (
    DuplicateYamlKeyError, canonical_json_sha256, files_sha256, load_strict_yaml, read_jsonl,
    write_jsonl,
)


class Color(Enum):
    RED = 'red'


def test_duplicate_yaml_keys_are_rejected(tmp_path) -> None:
    path = tmp_path / 'config.yaml'
    path.write_text('limits:\n  tokens: 128\n  tokens: 256\n')
    with pytest.raises(DuplicateYamlKeyError, match='tokens'):
        load_strict_yaml(path)


def test_jsonl_round_trip_preserves_key_order_and_converts_enums(tmp_path) -> None:
    path = tmp_path / 'rows.jsonl'
    write_jsonl(path, [{'second': Color.RED, 'first': (1, 2)}])
    [row] = read_jsonl(path)
    assert list(row) == ['second', 'first']
    assert row == {'second': 'red', 'first': [1, 2]}


def test_files_hash_ignores_listing_order_but_not_content(tmp_path) -> None:
    first, second = tmp_path / 'a.py', tmp_path / 'b.py'
    first.write_text('x = 1\n')
    second.write_text('y = 2\n')
    before = files_sha256([first, second])
    assert files_sha256([second, first]) == before
    second.write_text('y = 3\n')
    assert files_sha256([first, second]) != before


def test_canonical_json_hash_ignores_mapping_order() -> None:
    assert canonical_json_sha256({'a': 1, 'b': [Color.RED]}) == canonical_json_sha256(
        {'b': ['red'], 'a': 1})
