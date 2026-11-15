from dataclasses import replace
from pathlib import Path

from cybersos.app.about_content import artifact_paths
from cybersos.app.app_assets import AppAssets
from cybersos.app.demo_artifacts import prepare_demo_traces
from cybersos.app.evidence_content import EvidenceFiles, evidence_content, measured_report
from cybersos.domain import SessionMode
from cybersos.evaluation import load_traces, write_traces


def test_bundled_demos_are_real_saved_baseline_runs(app_assets: AppAssets) -> None:
    for key in app_assets.demos:
        content = evidence_content(app_assets, EvidenceFiles(), key, 'baseline')
        assert 'Recorded simulation only' in content.status
        assert 'R observed-state rule planner' in content.identity
        assert 'raw_proposal' in content.trace_text
        assert 'not run' in evidence_content(app_assets, EvidenceFiles(), key, 'trained').status


def test_saved_demo_generation_is_deterministic(app_assets: AppAssets, tmp_path: Path) -> None:
    first = prepare_demo_traces(app_assets, tmp_path / 'first.jsonl')
    second = prepare_demo_traces(app_assets, tmp_path / 'second.jsonl')
    assert first.read_bytes() == second.read_bytes()
    assert all(record.correct for record in load_traces(first))


def test_toggle_keeps_the_same_scenario_and_root(app_assets: AppAssets, tmp_path: Path) -> None:
    path = prepare_demo_traces(app_assets, tmp_path / 'traces.jsonl')
    records = load_traces(path)
    trained = tmp_path / 'trained.jsonl'
    write_traces(trained, [replace(record, identity=replace(record.identity, model_id='fixture-trained'))
                           for record in records])
    files = EvidenceFiles(baseline=path, trained=trained)
    baseline = evidence_content(app_assets, files, 'circular', 'baseline')
    result = evidence_content(app_assets, files, 'circular', 'trained')
    assert baseline.identity.split('Scenario:')[1] == result.identity.split('Scenario:')[1]
    write_traces(trained, [replace(records[0], case=replace(records[0].case, root_id='different-state'))])
    assert 'not run' in evidence_content(app_assets, files, 'circular', 'trained').status


def test_incident_traces_cannot_become_public_replay(app_assets: AppAssets, tmp_path: Path) -> None:
    path = prepare_demo_traces(app_assets, tmp_path / 'traces.jsonl')
    record = load_traces(path)[0]
    assert record.trace is not None
    write_traces(path, [replace(record, trace=replace(record.trace, mode=SessionMode.INCIDENT_GUIDANCE))])
    assert 'not run' in evidence_content(app_assets, EvidenceFiles(baseline=path), 'circular', 'baseline').status
    assert str(path.resolve()) not in artifact_paths(app_assets, EvidenceFiles(baseline=path))


def test_missing_metrics_stay_not_run_and_existing_report_is_shown(tmp_path: Path) -> None:
    assert 'not run' in measured_report(EvidenceFiles())
    report = tmp_path / 'measured.md'
    report.write_text('| Policy | Safe completion |\n| R | 2/3 |\n')
    assert '2/3' in measured_report(EvidenceFiles(report=report))
