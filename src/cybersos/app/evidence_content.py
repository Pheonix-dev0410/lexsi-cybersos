import json
from dataclasses import dataclass
from pathlib import Path

from cybersos.app.app_assets import ARTIFACT_DIRECTORY, AppAssets
from cybersos.app.demo_cases import DEMO_TEMPLATE_ID
from cybersos.data.scenario_fingerprints import root_hash
from cybersos.domain import Scenario, SessionMode
from cybersos.evaluation import TraceRecord, load_traces, render_results_tables
from cybersos.project_paths import REPORTS_DIR
from cybersos.serialization import to_json_value


@dataclass(frozen=True)
class EvidenceFiles:
    baseline: Path = ARTIFACT_DIRECTORY / 'baseline.jsonl'
    trained: Path | None = None
    report: Path | None = None


@dataclass(frozen=True)
class EvidenceContent:
    status: str
    identity: str
    trace_text: str


def _matches_demo(record: TraceRecord, scenario: Scenario) -> bool:
    return (record.case.scenario_id == scenario.scenario_id
            and record.case.root_id == root_hash(scenario, DEMO_TEMPLATE_ID)
            and record.case.expected_terminal == scenario.objective
            and record.case.opening_message == scenario.opening_message
            and record.trace is not None and record.trace.mode == SessionMode.BENCHMARK)


def evidence_content(assets: AppAssets, files: EvidenceFiles, demo_key: str,
                     selection: str) -> EvidenceContent:
    scenario = assets.demos[demo_key]
    expected_root = root_hash(scenario, DEMO_TEMPLATE_ID)
    path = files.baseline if selection == 'baseline' else files.trained
    missing = EvidenceContent('Simulation replay · not run for this scenario/checkpoint.',
                              'No saved generation is available.', '[]')
    if path is None or not path.is_file():
        return missing
    try:
        candidates = [record for record in load_traces(path) if _matches_demo(record, scenario)]
    except (ValueError, KeyError, TypeError, OSError):
        return EvidenceContent('Simulation replay unavailable: invalid saved artifact.', '', '[]')
    if len(candidates) != 1:
        return missing
    record = candidates[0]
    if record.trace is None or record.trace.mode != SessionMode.BENCHMARK:
        return missing
    identity = (f'{record.identity.model_id}\nCheckpoint: {record.identity.checkpoint_hash}\n'
                f'Run: {record.identity.run_id}\nContract: {record.identity.contract_hash}\n'
                f'Scenario: {scenario.scenario_id}\nRoot: {expected_root}')
    terminal = record.trace.terminal_state
    status = (f'Recorded simulation only · execution: {record.execution_status.value}; '
              f'outcome: {record.outcome.value}; '
              f'terminal: {terminal.value if terminal else "incomplete"}. '
              'This is saved evidence, not live model inference or real account recovery.')
    return EvidenceContent(status, identity, json.dumps(to_json_value(record.trace), indent=2))


def measured_report(files: EvidenceFiles) -> str:
    if files.report is not None and files.report.is_file():
        return 'Saved measured report · simulation evidence only\n\n' + files.report.read_text()
    return 'Measured evaluation: not run; no report artifact exists.\n\n' + render_results_tables({})


def default_report() -> Path | None:
    return next((path for path in (REPORTS_DIR / 'results.md', REPORTS_DIR / 'preflight.md')
                 if path.is_file()), None)


def is_public_trace_file(assets: AppAssets, path: Path) -> bool:
    try:
        records = load_traces(path)
    except (ValueError, KeyError, TypeError, OSError):
        return False
    scenarios = {scenario.scenario_id: scenario for scenario in assets.demos.values()}
    for record in records:
        scenario = scenarios.get(record.case.scenario_id)
        if scenario is None or not _matches_demo(record, scenario):
            return False
    return bool(records)
