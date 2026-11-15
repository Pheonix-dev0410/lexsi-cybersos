import copy
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

from cybersos.policy import (
    ServingContract, contract_hash, freeze_contract_pins, load_serving_contract,
)
from cybersos.project_paths import PROJECT_ROOT, SERVING_CONTRACT_PATH
from cybersos.serialization import file_sha256, to_json_value


def _leaves(data: Any, prefix: tuple[str | int, ...] = ()) -> Iterator[tuple[str | int, ...]]:
    if isinstance(data, dict) and data:
        for key, value in data.items():
            yield from _leaves(value, (*prefix, key))
    elif isinstance(data, list) and data:
        for index, value in enumerate(data):
            yield from _leaves(value, (*prefix, index))
    else:
        yield prefix


def test_every_frozen_field_contributes_to_contract_hash() -> None:
    fields = yaml.safe_load(SERVING_CONTRACT_PATH.read_text())
    original = contract_hash(fields)
    for path in _leaves(fields):
        changed = copy.deepcopy(fields)
        parent = changed
        for key in path[:-1]:
            parent = parent[key]
        parent[path[-1]] = {'changed': parent[path[-1]]}
        assert contract_hash(changed) != original, path


def test_hash_is_stable_across_mapping_order_and_contract_is_immutable() -> None:
    contract = load_serving_contract(SERVING_CONTRACT_PATH)
    mutable = to_json_value(contract.fields)
    reversed_order = dict(reversed(list(mutable.items())))
    assert contract_hash(reversed_order) == contract.contract_hash
    assert ServingContract(contract.fields).contract_hash == contract.contract_hash
    before = contract.contract_hash
    mutable['budgets']['actions'] = 1
    assert contract.contract_hash == before
    with pytest.raises(TypeError):
        contract.fields['budgets']['actions'] = 1


def test_output_keys_include_serving_model_and_case_identity() -> None:
    contract = load_serving_contract(SERVING_CONTRACT_PATH)
    b0 = {'base_revision': 'a' * 40, 'adapter_hash': None}
    b1 = {'base_revision': 'a' * 40, 'adapter_hash': 'b' * 64}
    assert contract.output_key(b0, case_id='case_a') != contract.output_key(b1, case_id='case_a')
    assert contract.output_key(b0, case_id='case_a') != contract.output_key(b0, case_id='case_b')


def test_placeholder_is_inspectable_but_cannot_be_used_for_a_run() -> None:
    load_serving_contract(SERVING_CONTRACT_PATH).validate_implementation(
        root=PROJECT_ROOT, require_resolved=True)
    fields = yaml.safe_load(SERVING_CONTRACT_PATH.read_text())
    fields['base_model']['revision'] = 'UNRESOLVED_BASE_REVISION'
    placeholder = ServingContract(fields)
    with pytest.raises(ValueError, match='immutable'):
        placeholder.validate_implementation(root=PROJECT_ROOT, require_resolved=True)


@pytest.mark.parametrize(('section', 'key', 'value'), [
    ('observations', 'mode', 'raw'), ('budgets', 'actions', 13),
    ('budgets', 'prompt_tokens', 2048), ('failure_policy', 'retries', 1),
    ('decoding', 'do_sample', True), ('serialization', 'template_applications', 2),
    ('rules', 'valid_action_filter', True), ('numerics', 'quantization', '4bit'),
])
def test_unsupported_settings_fail_closed(section: str, key: str, value: Any) -> None:
    fields = yaml.safe_load(SERVING_CONTRACT_PATH.read_text())
    fields[section][key] = value
    with pytest.raises(ValueError):
        ServingContract(fields)


@pytest.mark.parametrize(('section', 'key'), [('prompt', 'policy'), ('tools', 'definitions_text'),
                                           ('serialization', 'version')])
def test_runtime_detects_prompt_or_tool_contract_drift(section: str, key: str) -> None:
    fields = yaml.safe_load(SERVING_CONTRACT_PATH.read_text())
    fields[section][key] += 'changed'
    with pytest.raises(ValueError, match='differs|differ'):
        ServingContract(fields).validate_implementation(root=PROJECT_ROOT)


@pytest.fixture
def project_copy(tmp_path: Path) -> Path:
    """A copy of the contract and every file it pins, laid out like the project."""
    fields = yaml.safe_load(SERVING_CONTRACT_PATH.read_text())
    pinned = [fields['rules']['playbooks_path'], fields['rules']['sources_path'],
              *fields['guard']['files_sha256'], SERVING_CONTRACT_PATH.relative_to(PROJECT_ROOT)]
    for path in pinned:
        destination = tmp_path / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((PROJECT_ROOT / path).read_bytes())
    return tmp_path


def test_runtime_detects_corpus_and_guard_changes(project_copy: Path) -> None:
    fields = yaml.safe_load(SERVING_CONTRACT_PATH.read_text())
    contract = ServingContract(fields)
    contract.validate_implementation(root=project_copy)
    corpus = project_copy / fields['rules']['playbooks_path']
    corpus.write_text(corpus.read_text() + '\n')
    with pytest.raises(ValueError, match='corpus changed'):
        contract.validate_implementation(root=project_copy)
    fields['rules']['playbooks_sha256'] = file_sha256(corpus)
    guard = project_copy / next(iter(fields['guard']['files_sha256']))
    guard.write_text(guard.read_text() + '\n')
    with pytest.raises(ValueError, match='guard implementation changed'):
        ServingContract(fields).validate_implementation(root=project_copy)


def test_freezing_repins_only_changed_hashes_and_keeps_the_contract_text(project_copy: Path) -> None:
    contract_path = project_copy / SERVING_CONTRACT_PATH.relative_to(PROJECT_ROOT)
    fields = yaml.safe_load(contract_path.read_text())
    guard_path = next(iter(fields['guard']['files_sha256']))
    guard = project_copy / guard_path
    guard.write_text(guard.read_text() + '\n')
    before = contract_path.read_text()
    assert freeze_contract_pins(contract_path, root=project_copy) == {guard_path: file_sha256(guard)}
    load_serving_contract(contract_path)
    changed = [line for old, line in zip(before.splitlines(), contract_path.read_text().splitlines())
               if old != line]
    assert changed == [f'    {guard_path}: {file_sha256(guard)}']


def test_duplicate_and_missing_fields_are_rejected(tmp_path: Path) -> None:
    duplicate = tmp_path / 'duplicate.yaml'
    duplicate.write_text(SERVING_CONTRACT_PATH.read_text() + '\ncontract_version: cybersos-serving-v1\n')
    with pytest.raises(ValueError, match='Duplicate'):
        load_serving_contract(duplicate)
    fields = yaml.safe_load(SERVING_CONTRACT_PATH.read_text())
    del fields['rules']['retrieval']
    with pytest.raises(ValueError, match='fields'):
        ServingContract(fields)
