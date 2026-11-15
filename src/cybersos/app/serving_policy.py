from dataclasses import dataclass
from pathlib import Path

from cybersos.baselines import ObservedStatePlanner
from cybersos.evaluation.measured_model_policy import MeasuredModelPolicy
from cybersos.playbooks import PlaybookRegistry
from cybersos.policy import load_serving_contract
from cybersos.project_paths import PROJECT_ROOT
from cybersos.runtime import Policy

RULE_PLANNER_LABEL = 'R · observed-state rule planner; no model checkpoint'


@dataclass(frozen=True)
class ServingConfig:
    contract_path: Path | None = None
    base_manifest: Path | None = None
    adapter_path: Path | None = None


@dataclass(frozen=True)
class ServingModel:
    """The policy chosen once at startup. A session never switches policy after its episode begins."""
    model: Policy | None
    label: str


RULE_PLANNER = ServingModel(None, RULE_PLANNER_LABEL + ' (no model configured)')


def load_serving_model(config: ServingConfig) -> ServingModel:
    """Load and verify the configured weights before any session starts; fall back to R only here."""
    if config.contract_path is None:
        return RULE_PLANNER
    try:
        model = MeasuredModelPolicy(load_serving_contract(config.contract_path), root=PROJECT_ROOT,
                                    adapter_path=config.adapter_path, base_manifest=config.base_manifest)
        model.load_for_check()
    except Exception as error:
        return ServingModel(None, f'{RULE_PLANNER_LABEL} (model unavailable at startup: {type(error).__name__})')
    identity = model.identity
    return ServingModel(model, f'{identity.model_id} · base {identity.base_revision} · '
                               f'adapter {identity.adapter_hash or "none (base weights)"}')


def session_policy(serving: ServingModel, registry: PlaybookRegistry, required_steps: tuple[str, ...]) -> Policy:
    return serving.model if serving.model is not None else ObservedStatePlanner(registry, required_steps)
