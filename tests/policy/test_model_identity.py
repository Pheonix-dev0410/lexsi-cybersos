from pathlib import Path

import pytest

from cybersos.policy import adapter_hash
from cybersos.policy.model_identity import require_immutable_revision


def test_adapter_hash_is_portable_and_changes_with_weights_or_configuration(tmp_path: Path) -> None:
    first, second = tmp_path / 'first', tmp_path / 'second'
    for path in (first, second):
        path.mkdir()
        (path / 'adapter_config.json').write_text('{"r": 8}')
        (path / 'adapter_model.safetensors').write_bytes(b'explicit small weight fixture')
    digest = adapter_hash(first)
    assert digest == adapter_hash(second)
    (second / 'adapter_model.safetensors').write_bytes(b'different explicit weights')
    assert digest != adapter_hash(second)
    (first / 'adapter_config.json').write_text('{"r": 16}')
    assert digest != adapter_hash(first)


@pytest.mark.parametrize('revision', ['main', 'v1', 'abc123', '', 'A' * 40])
def test_mutable_or_unresolved_revisions_cannot_identify_a_model(revision: str) -> None:
    with pytest.raises(ValueError, match='immutable'):
        require_immutable_revision(revision)


def test_incomplete_adapter_is_rejected(tmp_path: Path) -> None:
    (tmp_path / 'adapter_config.json').write_text('{}')
    with pytest.raises(ValueError, match='weights'):
        adapter_hash(tmp_path)
