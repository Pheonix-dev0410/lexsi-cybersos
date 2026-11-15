from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from cybersos.evaluation.metrics import summarize, summarize_slices
from cybersos.evaluation.results_tables import PolicyResult, render_results_tables
from cybersos.evaluation.trace_records import TraceRecord


@dataclass(frozen=True)
class PreflightDecision:
    decision: str
    rationale: str
    frozen_protocol: Mapping[str, object]
    timings_seconds: Mapping[str, float]
    failure_categories: Mapping[str, int]


def write_preflight_report(path: str | Path, records: Mapping[str, Sequence[TraceRecord]], *,
                           decision: PreflightDecision, selected_model: str = 'B1',
                           missing_experiments: Mapping[str, str] | None = None) -> None:
    results = {}
    details = []
    for policy, rows in records.items():
        summary = summarize(rows)
        modes = sorted({r.trace.observation_mode for r in rows if r.trace})
        coverage = sorted({r.adjudication.free_text_coverage for r in rows})
        results[policy] = PolicyResult(summary, observation_mode=', '.join(modes) or 'not measured',
                                       free_text_coverage=', '.join(coverage) or 'not measured')
        details.append(f'{policy} cases:')
        details.append('| Scenario | Episode | Root | Execution | Outcome | Terminal | Safe success |')
        details.append('| --- | --- | --- | --- | --- | --- | --- |')
        for row in rows:
            cells = (row.case.scenario_id, row.case.episode_id, row.case.root_id,
                     row.execution_status.value, row.outcome.value,
                     row.trace.terminal_state.value if row.trace and row.trace.terminal_state else 'unknown',
                     str(row.safe_success))
            details.append('| ' + ' | '.join(value.replace('|', '\\|').replace('\n', ' ') for value in cells) + ' |')
        for name, sliced in summarize_slices(rows).items():
            details.append(f'{policy} slice {name}: scheduled={sliced.scheduled}; '
                           f'rates={sliced.rates}; execution={sliced.execution_statuses}; '
                           f'outcomes={sliced.task_outcomes}')
        details.append(f'{policy} efficiency (totals include failed attempts and retries): {summary.efficiency}')
    for policy, reason in (missing_experiments or {}).items():
        results[policy] = PolicyResult(None, gate_reason=reason)
    text = '\n\n'.join([
        'CyberSOS preflight', f'Decision: {decision.decision}', f'Rationale: {decision.rationale}',
        f'Frozen protocol: {dict(decision.frozen_protocol)}',
        f'Timings in seconds: {dict(decision.timings_seconds)}',
        f'Failure categories: {dict(decision.failure_categories)}',
        render_results_tables(results, selected_model=selected_model), '\n'.join(details),
    ])
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text + '\n', encoding='utf-8')
