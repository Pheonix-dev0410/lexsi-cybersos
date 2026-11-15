from collections.abc import Mapping

from cybersos.domain import AccessField, Availability, FactValue, Scenario
from cybersos.domain.factor_availability import effective_access_value


def scripted_access_answer(scenario: Scenario, field: AccessField, *,
                           access_state: Mapping[AccessField, FactValue] | None = None,
                           answer_overrides: Mapping[AccessField, FactValue] | None = None) -> FactValue:
    overrides = scenario.access_answers if answer_overrides is None else answer_overrides
    if field in overrides:
        return overrides[field]

    def answer(requested: AccessField) -> FactValue:
        if access_state is None or requested == AccessField.ACCOUNT_OWNER:
            return scenario.hidden_answer(requested)
        return access_state.get(requested, Availability.UNKNOWN)

    return effective_access_value(field, answer)
