import platform
from pathlib import Path
from typing import Any, Sequence

from cybersos.evaluation.auditkit_bridge import SCORER_VERSION
from cybersos.evaluation.efficiency_metrics import measured_total
from cybersos.evaluation.environment_provenance import environment_versions, vendor_commits
from cybersos.evaluation.metrics import summarize
from cybersos.evaluation.run_manifest import RunManifest
from cybersos.evaluation.trace_records import RunIdentity, TraceRecord
from cybersos.policy import ServingContract
from cybersos.serialization import file_sha256, write_json


def save_execution_manifest(destination: Path, records: Sequence[TraceRecord], *, identity: RunIdentity,
                            contract: ServingContract, hashes: dict[str, str], seed: int, timestamp: str,
                            model_evidence: dict[str, Any], cold_seconds: float | None,
                            generation_seconds: float | None, adapter_path: Path | None,
                            model_run: bool) -> None:
    fields = contract.fields
    environment_path = destination / 'environment.json'
    write_json(environment_path, environment_versions())
    digest = (model_evidence.get('identity', {}).get('adapter_hash') or identity.checkpoint_hash
              if adapter_path is not None else None)
    manifest = RunManifest(
        identity=identity,
        model_revision=fields['base_model']['revision'] if model_run else 'not applicable: rules',
        model_hash=((model_evidence.get('base_weight_sha256') or
                     'unmeasured; immutable Hub revision recorded separately') if model_run
                    else identity.checkpoint_hash),
        adapter_id=str(adapter_path) if adapter_path else None,
        adapter_revision=f'sha256:{digest}' if adapter_path else None, adapter_hash=digest,
        loaded_adapter_check=model_evidence, generation_calls=measured_total(records, 'generation_calls'),
        cache_hits=measured_total(records, 'cache_hits'), hashes=hashes, lexsi_commits=vendor_commits(),
        environment_lockfiles={str(environment_path): file_sha256(environment_path)},
        training_seeds=(), evaluation_seeds=(seed,), decoding=dict(fields['decoding']),
        hardware=platform.platform(),
        precision=fields['numerics']['precision'] if model_run else 'not applicable: rules',
        context_budget=fields['budgets']['context_tokens'], action_budget=fields['budgets']['actions'],
        scheduled=len(records), execution_statuses=summarize(records).execution_statuses,
        raw_trace_path=str(destination / 'traces.jsonl'), scorer_version=SCORER_VERSION,
        timestamp=timestamp, training_seconds=None, generation_seconds=generation_seconds,
        peak_memory_bytes=None, input_tokens=measured_total(records, 'input_tokens'),
        output_tokens=measured_total(records, 'output_tokens'), actual_billed_compute=None,
        cache_conditions={'generated_answers': 'disabled', 'retrieval': 'no shared cache'},
        cold_loading_seconds=cold_seconds, observation_mode=fields['observations']['mode'])
    write_json(destination / 'manifest.json', manifest)

