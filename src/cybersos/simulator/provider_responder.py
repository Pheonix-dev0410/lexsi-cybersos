from cybersos.domain import ProviderResponse, Scenario
from cybersos.playbooks import RecoveryRule


class ScriptedProvider:
    def __init__(self) -> None:
        self._positions: dict[str, int] = {}

    def respond(self, scenario: Scenario, rule: RecoveryRule) -> ProviderResponse:
        key = rule.id if rule.id in scenario.provider_script else rule.simulation_effect.value
        responses = scenario.provider_script.get(key, ())
        position = self._positions.get(key, 0)
        self._positions[key] = position + 1
        if position >= len(responses):
            return ProviderResponse.CHALLENGE
        if not scenario.account_owner:
            return ProviderResponse.DENIAL
        return responses[position]
