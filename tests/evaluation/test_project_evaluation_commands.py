from pathlib import Path
from typing import Any

import pytest
import yaml

from cybersos.evaluation import evaluation_command, load_traces
from cybersos.evaluation.evaluation_config import load_evaluation_config
from cybersos.evaluation.evaluation_command import evaluate
from cybersos.evaluation.results_report import report_results
from cybersos.evaluation.submission_inventory import check_submission
from cybersos.policy import load_serving_contract
from cybersos.project_paths import CONFIGS_DIR, DIAGNOSTIC_CASES_PATH, SERVING_CONTRACT_PATH
from cybersos.serialization import read_json

EVAL_CONFIG = CONFIGS_DIR / 'eval.yaml'


def test_shipped_eval_config_agrees_with_the_serving_contract() -> None:
    config = load_evaluation_config(EVAL_CONFIG, load_serving_contract())
    assert config.action_budget == load_serving_contract().fields['budgets']['actions']
    assert config.bootstrap_repetitions > 0


def test_conflicting_eval_settings_fail_before_any_generation(tmp_path: Path) -> None:
    config = yaml.safe_load(EVAL_CONFIG.read_text())
    config['decoding']['max_new_tokens'] = 256
    config['protocol']['timeout_seconds'] = 120
    conflicting = tmp_path / 'eval.yaml'
    conflicting.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match='max_new_tokens.*timeout_seconds'):
        load_evaluation_config(conflicting, load_serving_contract())


def test_cpu_evaluation_writes_trusted_traces_audit_and_identity(tmp_path: Path) -> None:
    output = tmp_path / 'runs'
    result = evaluate(EVAL_CONFIG, SERVING_CONTRACT_PATH, DIAGNOSTIC_CASES_PATH, output, split='dev', checkpoint='Q')
    run = Path(result['run'])
    rows = load_traces(run / 'traces.jsonl')
    manifest = read_json(run / 'manifest.json')
    assert len(rows) == result['safe_successes'] == 36
    assert all(row.identity.split == 'dev' for row in rows)
    assert manifest['adapter_id'] is None
    assert result['generation_calls'] is None and manifest['cache_hits'] is None
    assert manifest['hashes']['data'] != manifest['hashes']['split']
    assert manifest['scheduled'] == sum(manifest['execution_statuses'].values()) == 36
    assert all(row.final_state['objective_verified'] for row in rows)
    audit = read_json(run / 'auditkit.json')
    assert len(audit['state_assertions']['rows']) == len(audit['custom_predicates']['rows']) == 36
    report = report_results(output, tmp_path / 'report', load_evaluation_config(EVAL_CONFIG))
    assert '36/36' in report.read_text()
    with pytest.raises(ValueError, match='already exists'):
        evaluate(EVAL_CONFIG, SERVING_CONTRACT_PATH, DIAGNOSTIC_CASES_PATH, output, split='dev', checkpoint='Q')


def test_model_load_failure_writes_all_scheduled_cases_as_not_run(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable_weights(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError('weights unavailable on this machine')

    monkeypatch.setattr(evaluation_command, 'MeasuredModelPolicy', unavailable_weights)
    with pytest.raises(RuntimeError, match='Incomplete evaluation retained'):
        evaluate(EVAL_CONFIG, SERVING_CONTRACT_PATH, DIAGNOSTIC_CASES_PATH, tmp_path, split='dev', checkpoint='base')
    traces = next(tmp_path.rglob('traces.jsonl'))
    rows = load_traces(traces)
    assert len(rows) == 36
    assert all(row.execution_status.value == 'not_run' and not row.correct for row in rows)
    result = read_json(traces.with_name('execution.json'))
    assert result['generation_calls'] is None and 'weights unavailable' in result['failure']
    assert result['adapter_identity']['verified'] is False


def test_inspected_diagnostic_cases_cannot_be_used_as_final_test(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match='frozen test split'):
        evaluate(EVAL_CONFIG, SERVING_CONTRACT_PATH, DIAGNOSTIC_CASES_PATH, tmp_path, split='test', checkpoint='Q')


def test_submission_inventory_keeps_missing_and_optional_artifacts_explicit(tmp_path: Path) -> None:
    root = tmp_path / 'project'
    (root / 'reports').mkdir(parents=True)
    (root / 'reports/preflight.md').write_text('measured diagnostic results')
    result = check_submission(root, tmp_path / 'inventory')
    found = next(row for row in result['artifacts'] if row['artifact'] == 'Q/R results and diagnostic decision')
    assert found['status'] == 'exists'
    assert result['required_missing'] > 0
    optional = next(row for row in result['artifacts'] if row['optional'])
    assert optional['status'] == 'missing'
    assert 'does not establish' in result['scope']
