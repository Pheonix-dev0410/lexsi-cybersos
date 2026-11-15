import json
from pathlib import Path

from cybersos.domain import ExecutionStatus
from cybersos.evaluation.cost_worksheet import evaluation_seconds
from cybersos.evaluation.episode_checks import revision_handled
from cybersos.evaluation.recorded_runs import RecordedRun, check_weight_comparison, load_runs
from cybersos.evaluation.trace_records import TraceRecord
from cybersos.serialization import read_json

TARGET = 'revise route after an observed correction or provider failure'
RESERVATION_HEADROOM = 1.2


def report_sft_residuals(directory: Path, output: Path, *, remaining_seconds: float | None,
                         final_case_count: int) -> Path:
    """Name an AgentTune target only from measured development residuals, or state why training is skipped."""
    if final_case_count < 1 or (remaining_seconds is not None and remaining_seconds < 0):
        raise ValueError('Invalid evaluation reservation settings')
    runs = load_runs(directory)
    sft = [run for run in runs if run[1][0].identity.model_id == 'B1']
    if len(sft) > 1:
        raise ValueError('Select one development B1 sweep for residual analysis')
    reasons, targets, reservation = [], {}, None
    if not sft:
        reasons.append('No B1 development run; sequential residuals are unmeasured')
    else:
        targets, residual_reasons = _residual_targets(sft[0][1])
        reasons.extend(residual_reasons)
        reasons.extend(_matched_base_reasons(runs, sft[0]))
        reservation = _reserved_seconds(runs, final_case_count)
        if reservation is None:
            reasons.append('Complete B0/B1 timing evidence is needed to reserve final evaluation compute')
    if remaining_seconds is None:
        reasons.append('Remaining training/evaluation time has not been declared')
    elif reservation is not None and remaining_seconds <= reservation:
        reasons.append('Remaining time does not exceed the reserved final evaluation budget with 20% headroom')
    decision = 'AgentTune not run: ' + '; '.join(reasons) if reasons else (
        f'Target: {TARGET}\n'
        'REVIEW bounded training allocation and additional B2 evaluation reservation before the optional pilot')
    output.mkdir(parents=True, exist_ok=True)
    destination = output / 'sft_residuals.md'
    destination.write_text('CyberSOS SFT residual gate\n\n' + decision + '\n\nNamed sequential targets: ' +
                           json.dumps(targets, indent=2) + f'\n\nReserved B0/B1 evaluation seconds: {reservation}\n' +
                           'Any B2 sweep needs an additional measured reservation before training.\n')
    return destination


def _residual_targets(rows: tuple[TraceRecord, ...]) -> tuple[dict[str, object], list[str]]:
    if rows[0].identity.split != 'dev':
        raise ValueError('AgentTune selection must use development results only')
    verdicts = {row.case.episode_id: revision_handled(row) for row in rows if row.case.revision}
    failed = [row for row in rows if verdicts.get(row.case.episode_id) is False and
              row.execution_status == ExecutionStatus.FINISHED and
              not any(turn.parse_error for turn in row.trace.decisions)]
    reasons = []
    if not failed:
        reasons.append('No observed sequential revision residual supports AgentTune')
    if any(verdict is None for verdict in verdicts.values()):
        reasons.append('Some scripted revisions never fired; revision handling is untested for those cases')
    if any(row.execution_status != ExecutionStatus.FINISHED for row in rows):
        reasons.append('Incomplete B1 coverage requires repair before optional training')
    return {TARGET: {'episodes': [row.case.episode_id for row in failed],
                     'independent_roots': sorted({row.case.root_id for row in failed})}}, reasons


def _matched_base_reasons(runs: list[RecordedRun], sft: RecordedRun) -> list[str]:
    base = [run for run in runs if run[1][0].identity.model_id == 'B0']
    if len(base) != 1:
        return ['A matched B0 development run is required before the entrance decision']
    check_weight_comparison(base[0][0], sft[0])
    return []


def _reserved_seconds(runs: list[RecordedRun], final_case_count: int) -> float | None:
    """Mean measured seconds per case, cold loading included, scaled to the final suite with headroom."""
    measured = {}
    for path, rows in runs:
        label = rows[0].identity.model_id
        latencies = [row.measurements.latency_seconds for row in rows]
        if label in {'B0', 'B1'} and all(value is not None for value in latencies):
            cold = read_json(path.with_name('manifest.json'))['cold_loading_seconds'] or 0
            measured[label] = (sum(latencies) + cold) / len(rows)
    if len(measured) != 2:
        return None
    return evaluation_seconds(final_case_count, measured) * RESERVATION_HEADROOM
