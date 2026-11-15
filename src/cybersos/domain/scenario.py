from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from cybersos.domain.access import AccessField, Availability, FactValue, normalize_value
from cybersos.domain.frozen_values import freeze
from cybersos.domain.outcomes import ProviderResponse, TerminalState
from cybersos.domain.scenario_events import TemporaryToolFailure, UserCorrection


class Provider(StrEnum):
    GOOGLE_PERSONAL = 'google_personal'
    ANDROID = 'android'


class Incident(StrEnum):
    LOST_PHONE = 'lost_phone'
    LOST_SECOND_FACTOR = 'lost_second_factor'
    EXPOSED_PASSWORD = 'exposed_password'
    LOCKOUT = 'lockout'


@dataclass(frozen=True)
class Permissions:
    destructive_actions_enabled: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.destructive_actions_enabled, bool):
            raise ValueError('Destructive permission must be boolean')


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    provider: Provider
    incident: Incident
    account_owner: bool
    access: Mapping[AccessField | str, object]
    provider_script: Mapping[str, ProviderResponse | str | tuple[str, ...]] = field(default_factory=dict)
    permissions: Permissions = field(default_factory=Permissions)
    initial_facts: Mapping[AccessField | str, object] = field(default_factory=dict)
    opening_message: str = ''
    required_protective_steps: tuple[str, ...] = ()
    objective: TerminalState | None = None
    corrections: tuple[UserCorrection, ...] = ()
    temporary_tool_failures: tuple[TemporaryToolFailure, ...] = ()
    access_answers: Mapping[AccessField | str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.account_owner, bool) or not isinstance(self.permissions, Permissions):
            raise ValueError('Ownership and permissions must be explicitly typed')
        if not isinstance(self.scenario_id, str) or not self.scenario_id:
            raise ValueError('scenario_id must be a nonempty string')
        object.__setattr__(self, 'provider', Provider(self.provider))
        object.__setattr__(self, 'incident', Incident(self.incident))
        for name in ('access', 'initial_facts', 'access_answers'):
            values = {AccessField(key): normalize_value(AccessField(key), value)
                      for key, value in getattr(self, name).items()}
            object.__setattr__(self, name, freeze(values))
        for name, record in (('corrections', UserCorrection),
                             ('temporary_tool_failures', TemporaryToolFailure)):
            object.__setattr__(self, name, tuple(
                item if isinstance(item, record) else record(**item)
                for item in getattr(self, name)))
        script = {key: tuple(ProviderResponse(item) for item in
                            (value if isinstance(value, (tuple, list)) else (value,)))
                  for key, value in self.provider_script.items()}
        object.__setattr__(self, 'provider_script', freeze(script))
        object.__setattr__(self, 'required_protective_steps', tuple(self.required_protective_steps))
        if self.objective is not None:
            object.__setattr__(self, 'objective', TerminalState(self.objective))

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> 'Scenario':
        data = dict(values)
        data['permissions'] = Permissions(**data.get('permissions', {}))
        return cls(**data)

    def hidden_answer(self, field: AccessField) -> FactValue:
        if field == AccessField.ACCOUNT_OWNER:
            return Availability.from_value(self.account_owner)
        return self.access.get(field, Availability.UNKNOWN)
