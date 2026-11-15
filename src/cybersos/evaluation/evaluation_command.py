from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any

from cybersos.baselines import GuidedQuestionnaire, ObservedStatePlanner
from cybersos.data.diagnostic_scenarios import DiagnosticCase, load_diagnostic_scenarios
from cybersos.data.scenario_fingerprints import state_hash
from cybersos.evaluation.auditkit_bridge import evaluate_recorded
from cybersos.evaluation.batch_runner import run_batch, schedule_cases
from cybersos.evaluation.efficiency_metrics import measured_total
from cybersos.evaluation.evaluation_config import load_evaluation_config
from cybersos.evaluation.execution_manifest import save_execution_manifest
from cybersos.evaluation.measured_model_policy import MeasuredModelPolicy
from cybersos.evaluation.metrics import summarize
from cybersos.evaluation.model_load_check import check_in_fresh_process
from cybersos.evaluation.run_versions import rule_baseline_checkpoint, run_key, version_hashes
from cybersos.evaluation.trace_records import RunIdentity, TraceRecord
from cybersos.playbooks import load_project_registry
from cybersos.policy import adapter_hash, load_serving_contract
from cybersos.project_paths import DIAGNOSTIC_CASES_PATH, PROJECT_ROOT
from cybersos.runtime import Policy
from cybersos.serialization import canonical_json_sha256, read_jsonl, write_json

RULE_POLICIES = {'Q': GuidedQuestionnaire, 'R': ObservedStatePlanner}


def evaluate(config_path: Path, contract_path: Path, cases_path: Path, output: Path, *,
             split: str, checkpoint: str, policy_label: str = 'B1',
             base_manifest: Path | None = None) -> dict[str, Any]:
    contract = load_serving_contract(contract_path)
    config = load_evaluation_config(config_path, contract)
    cases = schedule_cases(_load_split(cases_path, split, config.case_count))
    label = checkpoint if checkpoint in RULE_POLICIES else 'B0' if checkpoint == 'base' else policy_label
    adapter = None if checkpoint in {*RULE_POLICIES, 'base'} else Path(checkpoint).resolve()
    digest = (adapter_hash(adapter) if adapter else canonical_json_sha256(contract.fields['base_model'])
              if checkpoint == 'base' else rule_baseline_checkpoint())
    hashes = version_hashes(contract, cases_path=cases_path, split=split, config_path=config_path,
                            episode_ids=[case.info.episode_id for case in cases])
    key = run_key(hashes, contract, checkpoint_hash=digest, seed=config.seed)[:16]
    destination = output / split / f'{label}-{key}'
    if (destination / 'traces.jsonl').exists():
        raise ValueError(f'Run already exists; preserve the declared sweep: {destination}')
    destination.mkdir(parents=True, exist_ok=True)
    identity = RunIdentity(f'{split}-{label}-{key}', label, digest, contract.contract_hash, split)
    model, factory, evidence, failure = None, None, {'verified': True, 'kind': 'deterministic rules'}, None
    registry = load_project_registry()
    if checkpoint in RULE_POLICIES:
        factory = lambda: RULE_POLICIES[checkpoint](registry)
    else:
        model, factory, evidence, failure = _verified_model(contract_path, destination, adapter, base_manifest)
    started = monotonic()
    rows = run_batch(cases, factory, registry, identity, action_budget=config.action_budget,
                     trace_path=destination / 'traces.jsonl')
    elapsed = monotonic() - started
    summary = summarize(rows)
    write_json(destination / 'summary.json', summary)
    write_json(destination / 'serving_contract.json', contract.fields)
    save_execution_manifest(destination, rows, identity=identity, contract=contract, hashes=hashes,
                            seed=config.seed, timestamp=datetime.now(timezone.utc).isoformat(),
                            model_evidence=evidence, cold_seconds=_cold_seconds(model, evidence),
                            generation_seconds=model.generation_seconds if model else None,
                            adapter_path=adapter, model_run=checkpoint not in RULE_POLICIES)
    failures = [message for message in (failure, _audit(rows, destination, factory is not None)) if message]
    result = {'run': str(destination), 'scheduled': len(rows), 'execution_statuses': summary.execution_statuses,
              'safe_successes': sum(row.safe_success for row in rows), 'elapsed_seconds': elapsed,
              'generation_calls': measured_total(rows, 'generation_calls'),
              'cache_hits': measured_total(rows, 'cache_hits'),
              'adapter_identity': evidence, 'failure': '; '.join(failures) or None}
    write_json(destination / 'execution.json', result)
    if failures or any(row.execution_status.value != 'finished' for row in rows):
        raise RuntimeError(f'Incomplete evaluation retained at {destination}: '
                           f'{result["failure"] or summary.execution_statuses}')
    return result


def _load_split(cases_path: Path, split: str, case_count: int) -> tuple[DiagnosticCase, ...]:
    authored = load_diagnostic_scenarios(cases_path)
    raw_rows = read_jsonl(cases_path)
    if any(row.get('split') in {'dev', 'test', 'train'} and row['split'] != split for row in raw_rows):
        raise ValueError('Scenario split labels differ from the requested evaluation split')
    if split != 'test':
        return authored
    if any(row.get('split') != 'test' or row.get('family') or 'diagnostic' in row.get('tags', ())
           for row in raw_rows):
        raise ValueError('Final test requires an explicit frozen test split without inspected diagnostic roots')
    if len(authored) != case_count:
        raise ValueError('Final test case count differs from the frozen evaluation config')
    inspected = load_diagnostic_scenarios(DIAGNOSTIC_CASES_PATH)
    if ({case.root.root_id for case in authored} & {case.root.root_id for case in inspected} or
            {state_hash(case.scenario) for case in authored} & {state_hash(case.scenario) for case in inspected}):
        raise ValueError('Inspected diagnostic roots cannot enter the final test')
    return authored


def _verified_model(contract_path: Path, destination: Path, adapter: Path | None, base_manifest: Path | None
                    ) -> tuple[MeasuredModelPolicy | None, Callable[[], Policy] | None, dict[str, Any], str | None]:
    """Load once here and once in a fresh process; a failure leaves every case scheduled but not run."""
    model = None
    try:
        model = MeasuredModelPolicy(load_serving_contract(contract_path), root=PROJECT_ROOT,
                                    adapter_path=adapter, base_manifest=base_manifest)
        reload = check_in_fresh_process(contract_path, destination / 'load_check.json',
                                        adapter=adapter, base_manifest=base_manifest)
        model.load_for_check()
        if reload['identity'] != model.loaded_identity['identity']:
            raise ValueError('Fresh-process identity differs from inference identity')
        verified = model
        return model, lambda: verified, model.loaded_identity | {'fresh_process': True, 'reload_check': reload}, None
    except Exception as error:
        failure = f'{type(error).__name__}: {error}'
        return model, None, {'verified': False, 'fresh_process': False, 'error': failure,
                             'identity': model.identity.as_dict() if model else {}}, failure


def _cold_seconds(model: MeasuredModelPolicy | None, evidence: dict[str, Any]) -> float | None:
    if model is None:
        return None
    return model.cold_loading_seconds + evidence.get('reload_check', {}).get('cold_loading_seconds', 0)


def _audit(rows: tuple[TraceRecord, ...], destination: Path, reset_confirmed: bool) -> str | None:
    try:
        scored = evaluate_recorded(rows, reset_confirmed=reset_confirmed)
    except Exception as error:
        return f'AuditKIT: {type(error).__name__}: {error}'
    write_json(destination / 'auditkit.json', {'state_assertions': scored.state_assertions.to_dict(),
                                               'custom_predicates': scored.custom_predicates.to_dict()})
    return None

