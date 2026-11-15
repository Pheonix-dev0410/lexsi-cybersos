from dataclasses import dataclass
from typing import Mapping

from cybersos.domain import ExecutionStatus
from cybersos.evaluation.trace_records import RunIdentity
from cybersos.serialization import canonical_json_sha256


@dataclass(frozen=True)
class RunManifest:
    identity: RunIdentity
    model_revision: str
    model_hash: str
    adapter_id: str | None
    adapter_revision: str | None
    adapter_hash: str | None
    loaded_adapter_check: Mapping[str, object]
    generation_calls: int | None
    cache_hits: int | None
    hashes: Mapping[str, str]
    lexsi_commits: Mapping[str, str]
    environment_lockfiles: Mapping[str, str]
    training_seeds: tuple[int, ...]
    evaluation_seeds: tuple[int, ...]
    decoding: Mapping[str, object]
    hardware: str
    precision: str
    context_budget: int
    action_budget: int
    scheduled: int
    execution_statuses: Mapping[str, int]
    raw_trace_path: str
    scorer_version: str
    timestamp: str
    training_seconds: float | None
    generation_seconds: float | None
    peak_memory_bytes: int | None
    input_tokens: int | None
    output_tokens: int | None
    actual_billed_compute: float | None
    cache_conditions: Mapping[str, object]
    cold_loading_seconds: float | None
    observation_mode: str
    schema_version: str = 'cybersos.manifest.v1'

    def __post_init__(self) -> None:
        required = {'data', 'split', 'source_corpus', 'prompt', 'simulator', 'tools', 'guard', 'runtime'}
        if not required <= self.hashes.keys() or not all(self.hashes[key] for key in required):
            raise ValueError(f'Manifest hashes require {sorted(required)}')
        statuses = {status.value for status in ExecutionStatus}
        if set(self.execution_statuses) != statuses or any(v < 0 for v in self.execution_statuses.values()):
            raise ValueError('Every execution status must be present with a nonnegative count')
        if sum(self.execution_statuses.values()) != self.scheduled:
            raise ValueError('Execution status counts must sum to scheduled cases')
        if not self.loaded_adapter_check or not self.evaluation_seeds or not self.timestamp:
            raise ValueError('Loaded identity check, evaluation seeds and explicit timestamp required')
        if self.adapter_id and not all((self.adapter_revision, self.adapter_hash)):
            raise ValueError('Adapter runs require revision and weight hash')
        if not all((self.lexsi_commits, self.environment_lockfiles, self.hardware, self.precision,
                    self.raw_trace_path, self.scorer_version, self.observation_mode)):
            raise ValueError('Reproducibility evidence must be declared')
        if not 1 <= self.action_budget <= 12 or self.context_budget < 1:
            raise ValueError('Invalid context or action budget')
        for value in (self.generation_calls, self.cache_hits, self.training_seconds, self.generation_seconds,
                      self.peak_memory_bytes, self.input_tokens, self.output_tokens, self.actual_billed_compute):
            if value is not None and value < 0:
                raise ValueError('Manifest measurements must be nonnegative')


def output_cache_key(*, checkpoint_hash: str, prompt_version: str, tool_version: str,
                     source_version: str, guard_version: str, runtime_version: str,
                     scenario_revision: str, observation_revision: str, observation_mode: str,
                     decoding: Mapping[str, object], seed: int) -> str:
    return canonical_json_sha256(locals())
