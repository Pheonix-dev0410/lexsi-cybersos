from dataclasses import replace
from pathlib import Path

import pytest

from cybersos.domain import ExecutionStatus
from cybersos.evaluation import RunIdentity, RunManifest, output_cache_key
from cybersos.serialization import read_json, write_json


def test_manifest_requires_complete_status_denominator_and_adapter_identity(tmp_path: Path) -> None:
    manifest = RunManifest(
        identity=RunIdentity('sft-run', 'B1', 'adapter-sha', 'contract-sha'),
        model_revision='base-rev', model_hash='base-sha', adapter_id='sft',
        adapter_revision='sft-rev', adapter_hash='adapter-sha',
        loaded_adapter_check={'fresh_process': True, 'loaded_hash': 'adapter-sha'},
        generation_calls=2, cache_hits=0,
        hashes={key: key + '-sha' for key in ('data', 'split', 'source_corpus', 'prompt',
                                             'simulator', 'tools', 'guard', 'runtime')},
        lexsi_commits={'AuditKIT': 'pinned'}, environment_lockfiles={'requirements.lock': 'sha'},
        training_seeds=(1,), evaluation_seeds=(2,), decoding={'do_sample': False},
        hardware='CPU test', precision='float32', context_budget=4096, action_budget=12,
        scheduled=1, execution_statuses={s.value: int(s == ExecutionStatus.FINISHED) for s in ExecutionStatus},
        raw_trace_path='reports/traces.jsonl', scorer_version='v1', timestamp='2026-11-15T00:00:00Z',
        training_seconds=None, generation_seconds=2, peak_memory_bytes=None,
        input_tokens=100, output_tokens=30, actual_billed_compute=None,
        cache_conditions={'generated_answer_cache': False}, cold_loading_seconds=1,
        observation_mode='structured')
    output = tmp_path / 'manifest.json'
    write_json(output, manifest)
    assert read_json(output)['adapter_hash'] == 'adapter-sha'
    with pytest.raises(ValueError, match='sum'):
        replace(manifest, scheduled=2)
    with pytest.raises(ValueError, match='weight hash'):
        replace(manifest, adapter_hash=None)


def test_output_cache_identity_covers_all_contract_changes() -> None:
    base = dict(checkpoint_hash='b0', prompt_version='p', tool_version='t', source_version='s',
                guard_version='g', runtime_version='r', scenario_revision='case1',
                observation_revision='obs1', observation_mode='structured',
                decoding={'temperature': 0}, seed=7)
    key = output_cache_key(**base)
    assert key == output_cache_key(**base)
    for field in base:
        changed = dict(base)
        changed[field] = 8 if field == 'seed' else {'temperature': 1} if field == 'decoding' else 'changed'
        assert output_cache_key(**changed) != key
