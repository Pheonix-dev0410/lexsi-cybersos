from dataclasses import dataclass
from pathlib import Path

from cybersos.data.diagnostic_scenarios import DiagnosticCase, load_diagnostic_scenarios
from cybersos.domain import ExecutionStatus
from cybersos.evaluation import RunIdentity
from cybersos.evaluation.batch_runner import run_batch, schedule_cases
from cybersos.playbooks import load_project_registry
from cybersos.policy import ServingContract, TransformersPolicy, load_serving_contract
from cybersos.policy.model_identity import MODEL_ID
from cybersos.serialization import write_json


SMOKE_EPISODES = 20


@dataclass(frozen=True)
class DevelopmentInputs:
    contract: ServingContract
    cases: tuple[DiagnosticCase, ...]


def load_development_inputs(contract_path: str | Path,
                            development_path: str | Path) -> DevelopmentInputs:
    """Check before training that a smoke run can be evaluated on declared development episodes."""
    contract = load_serving_contract(contract_path, require_resolved=True)
    cases = load_diagnostic_scenarios(development_path)
    if len(cases) < SMOKE_EPISODES or any(
            case.split not in {'dev', 'prompt_dev', 'diagnostic'} for case in cases):
        raise ValueError('Smoke evaluation requires at least twenty declared development episodes')
    return DevelopmentInputs(contract, cases[:SMOKE_EPISODES])


def run_development_smoke(inputs: DevelopmentInputs, adapter_path: str | Path, adapter_hash: str, *,
                          base_manifest: str | Path, label: str) -> dict[str, object]:
    """Run a reloaded adapter on development episodes; any infrastructure failure fails the run."""
    destination = Path(adapter_path)
    policy = TransformersPolicy(inputs.contract, adapter_path=destination, base_manifest=base_manifest)
    identity = RunIdentity(f'{label}-smoke-development', MODEL_ID, adapter_hash,
                           inputs.contract.contract_hash)
    records = run_batch(schedule_cases(inputs.cases), lambda: policy, load_project_registry(),
                        identity, action_budget=inputs.contract.fields['budgets']['actions'],
                        trace_path=destination / 'smoke_development_traces.jsonl')
    failed = [record.case.episode_id for record in records
              if record.execution_status != ExecutionStatus.FINISHED]
    result = {'episodes': len(records), 'infrastructure_failures': failed,
              'passed': not failed, 'contract_hash': inputs.contract.contract_hash}
    write_json(destination / 'smoke_development.json', result)
    if failed:
        raise RuntimeError(f'{label} smoke had infrastructure failures in {len(failed)} development episodes')
    return result
