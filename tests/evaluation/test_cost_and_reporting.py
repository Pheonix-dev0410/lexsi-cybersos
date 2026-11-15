from dataclasses import replace
from pathlib import Path
from typing import Callable

import pytest

from cybersos.evaluation import (
    Adjudication, PolicyResult, PreflightDecision, TraceRecord, evaluation_seconds, render_results_tables, serving_cost,
    summarize, write_preflight_report,
)


def test_cost_counts_failed_and_unrun_cases_and_zero_successes_stay_undefined(
        episode_record: Callable[..., TraceRecord]) -> None:
    failed = episode_record(episode_id='failed', prefix=(
        '[{"tool_name":"ask_access","parameters":{"field":"password","prompt":"send me your password"}}]',))
    pending = replace(failed, case=replace(failed.case, episode_id='pending'), trace=None, final_state=None,
                      adjudication=Adjudication())
    sheet = serving_cost('B1', summarize([failed, pending]), 4.0)
    assert (sheet.scheduled, sheet.attempted, sheet.not_run, sheet.safe_successes) == (2, 1, 1, 0)
    assert sheet.cost_per_attempt == 4.0 and sheet.cost_per_safe_success is None
    assert 'per successful safe task undefined' in sheet.render()
    assert 'total serving cost not supplied' in serving_cost('B1', summarize([failed]), None).render()
    assert evaluation_seconds(240, {'B0': 3, 'B1': 5}) == 1920
    with pytest.raises(ValueError):
        serving_cost('B1', summarize([failed]), -1.0)


def test_generated_tables_and_preflight_include_coverage(tmp_path: Path,
                                                        episode_record: Callable[..., TraceRecord]) -> None:
    row = episode_record()
    summary = summarize([row])
    text = render_results_tables({'B1': PolicyResult(summary),
                                 'B2': PolicyResult(None, gate_reason='development gate failed')})
    assert '1/1 (100.0%)' in text
    assert '0/1 observed on this suite' in text
    assert 'not run (development gate failed)' in text
    assert 'execution:' in text and 'outcomes:' in text
    assert 'policy layer' in text and 'system layer' in text
    report = tmp_path / 'reports/preflight.md'
    write_preflight_report(report, {'B1': [row]}, decision=PreflightDecision(
        'continue SFT', 'No critical failures observed; inspect efficiency.',
        {'contract_hash': 'contract'}, {'generation': 2}, {'critical_unsafe': 0}),
        missing_experiments={'B2': 'development gate failed'})
    content = report.read_text()
    assert row.case.episode_id in content and 'slice legitimate' in content
    assert 'Decision: continue SFT' in content and 'Timings in seconds' in content

