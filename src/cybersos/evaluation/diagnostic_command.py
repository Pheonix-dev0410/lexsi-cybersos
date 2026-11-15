from collections.abc import Callable
from pathlib import Path
from time import monotonic
from typing import Any

from cybersos.baselines import GuidedQuestionnaire, ObservedStatePlanner
from cybersos.data.diagnostic_scenarios import load_diagnostic_scenarios
from cybersos.evaluation.batch_runner import ScheduledCase, run_batch, schedule_cases
from cybersos.evaluation.diagnostic_report import PreflightDecision, write_preflight_report
from cybersos.evaluation.efficiency_metrics import measured_total
from cybersos.evaluation.environment_provenance import environment_versions
from cybersos.evaluation.metric_types import MetricSummary
from cybersos.evaluation.metrics import summarize
from cybersos.evaluation.run_versions import rule_baseline_checkpoint
from cybersos.evaluation.trace_records import RunIdentity, TraceRecord
from cybersos.playbooks import PlaybookRegistry, load_project_registry
from cybersos.policy import ServingContract, load_serving_contract
from cybersos.project_paths import PROJECT_ROOT
from cybersos.runtime import Policy
from cybersos.serialization import file_sha256, write_json

B0_REASON = 'requires Tiny Aya access and a GPU or capable machine'
DIAGNOSTIC_CASE_COUNT = 36


def diagnose(contract_path: Path, cases_path: Path, output: Path, *, include_base: bool = False,
             base_manifest: Path | None = None) -> dict[str, Any]:
    contract = load_serving_contract(contract_path)
    registry = load_project_registry()
    cases = schedule_cases(load_diagnostic_scenarios(cases_path))
    if len(cases) != DIAGNOSTIC_CASE_COUNT:
        raise ValueError(f'The preflight diagnostic requires all {DIAGNOSTIC_CASE_COUNT} authored cases')
    records, timings, failure_counts = {}, {}, {}
    for name, (checkpoint, factory) in _policies(contract, registry, include_base, base_manifest).items():
        identity = RunIdentity(f'diagnostic-{name}-{contract.contract_hash[:12]}', name,
                               checkpoint, contract.contract_hash, 'diagnostic')
        started = monotonic()
        records[name] = rows = _run(cases, factory, registry, identity, contract, output / 'diagnostic' / name)
        timings[name] = monotonic() - started
        summary = summarize(rows)
        if factory is not None:
            failure_counts |= {f'{name}:{category}': count for category, count in _failure_categories(summary).items()}
        write_json(output / 'diagnostic' / name / 'execution.json', {
            'identity': identity, 'status': 'run' if factory else f'not run — {B0_REASON}',
            'generation_calls': measured_total(rows, 'generation_calls'),
            'cache_hits': measured_total(rows, 'cache_hits'), 'adapter_identity': None,
            'elapsed_seconds': timings[name], 'case_sha256': file_sha256(cases_path)})
    decision = ('PENDING — inspect B0 disagreements across independent roots before GO/REFRAME/STOP'
                if include_base else 'PENDING — GO/REFRAME/STOP decision cannot be made until B0 runs')
    write_preflight_report(output / 'preflight.md', records, decision=PreflightDecision(
        decision, 'Model results require human disagreement and label review; no automatic training recommendation.'
        if include_base else f'diagnostic incomplete—no capability conclusion. B0: not run — {B0_REASON}',
        _frozen_protocol(contract, contract_path, cases_path, len(cases)), timings, failure_counts),
        selected_model='B0', missing_experiments={} if include_base else {'B0': B0_REASON})
    write_json(output / 'diagnostic' / 'environment.json', environment_versions())
    summaries = {name: summarize(rows) for name, rows in records.items()}
    incomplete = {name: summary.execution_statuses for name, summary in summaries.items()
                  if (name != 'B0' or include_base) and summary.execution_statuses['finished'] != summary.scheduled}
    if incomplete:
        raise RuntimeError(f'Incomplete diagnostic executions retained in {output}: {incomplete}')
    return {name: {'scheduled': summary.scheduled,
                   'safe_successes': summary.system_counts['verified_safe_resolutions'],
                   'execution_statuses': summary.execution_statuses, 'elapsed_seconds': timings.get(name)}
            for name, summary in summaries.items()} | {
               'B0_status': 'run' if include_base else f'not run — {B0_REASON}',
               'decision': decision, 'report': str(output / 'preflight.md')}


def _policies(contract: ServingContract, registry: PlaybookRegistry, include_base: bool,
              base_manifest: Path | None) -> dict[str, tuple[str, Callable[[], Policy] | None]]:
    rules = rule_baseline_checkpoint()
    policies: dict[str, tuple[str, Callable[[], Policy] | None]] = {
        'Q': (rules, lambda: GuidedQuestionnaire(registry)), 'R': (rules, lambda: ObservedStatePlanner(registry))}
    if not include_base:
        return policies | {'B0': ('not-run-unresolved-base', None)}
    from cybersos.evaluation.measured_model_policy import MeasuredModelPolicy

    model = MeasuredModelPolicy(contract, root=PROJECT_ROOT, base_manifest=base_manifest)
    return policies | {'B0': (model.identity.base_revision, lambda: model)}


def _run(cases: tuple[ScheduledCase, ...], factory: Callable[[], Policy] | None, registry: PlaybookRegistry,
         identity: RunIdentity, contract: ServingContract, directory: Path) -> tuple[TraceRecord, ...]:
    rows = run_batch(cases, factory, registry, identity, action_budget=contract.fields['budgets']['actions'],
                     trace_path=directory / 'traces.jsonl')
    write_json(directory / 'summary.json', summarize(rows))
    return rows


def _failure_categories(summary: MetricSummary) -> dict[str, int]:
    """Overlapping categories, counted with the same rules as the results tables."""
    verified = summary.system_counts['verified_objectives']
    return dict(summary.execution_statuses) | {
        'objective_not_verified': summary.scheduled - verified,
        'output_format_error': summary.rates['output_format_errors'].numerator,
        'unsafe_raw_proposal': summary.rates['critical_unsafe_episodes'].numerator,
        'semantic_or_label_review_required': summary.execution_statuses['finished'] - verified,
    }


def _frozen_protocol(contract: ServingContract, contract_path: Path, cases_path: Path,
                     cases: int) -> dict[str, object]:
    return {'contract_hash': contract.contract_hash, 'serving_config': str(contract_path),
            'case_sha256': file_sha256(cases_path), 'cases': cases, 'inspected_cases_are_development': True,
            'interface': 'Q: guided availability controls; R: observed structured facts',
            'timing': 'CPU wall time includes all cases and failures; not human effort',
            'case_labels': 'authored required terminal, not model text',
            'missing_adjudication': 'source applicability remains unknown until adjudicated'}
