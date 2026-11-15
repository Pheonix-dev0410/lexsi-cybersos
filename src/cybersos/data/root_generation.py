from dataclasses import replace
from functools import cache

from cybersos.data.base_access_state import counterfactual_value
from cybersos.serialization import canonical_json_sha256
from cybersos.data.scenario_fingerprints import root_hash
from cybersos.data.scenario_records import ScenarioRoot
from cybersos.data.state_templates import TEMPLATES, StateTemplate, template_scenario
from cybersos.domain import Scenario, TerminalState


PROTECTIVE_STEPS = {'android_online': 'secure_android_device',
                    'exposed_remaining_access': 'change_exposed_password'}


def make_root(scenario: Scenario, template_id: str, template: StateTemplate, *,
              pair_id: str | None = None, eligible: bool = False,
              independent: bool = False) -> ScenarioRoot:
    digest = root_hash(scenario, template_id)
    scenario = replace(scenario, scenario_id=f'root-{digest}')
    return ScenarioRoot(scenario, f'root-{digest}', digest, template_id, template.bucket,
                        template.tags, pair_id, template.paired_field, eligible, independent)


def _pair_member(base: Scenario, template: StateTemplate, available: bool) -> Scenario:
    field = template.paired_field
    access = dict(base.access) | {field: counterfactual_value(field, available)}
    protective = PROTECTIVE_STEPS.get(template.name)
    if not available:
        objective = TerminalState.OFFICIAL_RECOVERY_PENDING
    elif protective:
        objective = TerminalState.PROTECTIVE_WORKFLOW_COMPLETED
    else:
        objective = TerminalState.SIMULATED_ACCESS_RESTORED
    return replace(base, access=access, objective=objective,
                   required_protective_steps=(protective,) if protective else ())


@cache
def generate_roots() -> tuple[ScenarioRoot, ...]:
    roots: dict[str, ScenarioRoot] = {}
    for template in TEMPLATES:
        for variant in range(128):
            base = template_scenario(template, variant)
            if template.paired_field is None:
                root = make_root(base, template.name, template)
                roots[root.root_id] = root
                continue
            pair_id = canonical_json_sha256({'template': template.name,
                                    'base': root_hash(base, template.name)})
            for available in (False, True):
                eligible = available and template.name not in PROTECTIVE_STEPS
                root = make_root(_pair_member(base, template, available), template.name, template,
                                 pair_id=pair_id, eligible=eligible)
                roots[root.root_id] = root
    return tuple(roots.values())
