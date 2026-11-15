from typing import Any

from cybersos.domain import Scenario
from cybersos.serialization import canonical_json_sha256, to_json_value


# Wording, identity and the expected outcome do not define a hidden state.
NON_STATE_KEYS = ('scenario_id', 'opening_message', 'objective')


def scenario_mapping(scenario: Scenario) -> dict[str, Any]:
    return to_json_value(scenario)


def state_mapping(scenario: Scenario) -> dict[str, Any]:
    values = scenario_mapping(scenario)
    for key in NON_STATE_KEYS:
        values.pop(key)
    return values


def state_hash(scenario: Scenario) -> str:
    return canonical_json_sha256(state_mapping(scenario))


def root_hash(scenario: Scenario, template_id: str) -> str:
    return canonical_json_sha256({'state_hash': state_hash(scenario), 'template_id': template_id})


def paraphrase_hash(message: str) -> str:
    return canonical_json_sha256(' '.join(message.casefold().split()))
