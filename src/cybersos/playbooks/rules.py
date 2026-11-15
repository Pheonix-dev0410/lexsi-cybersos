from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Mapping

from cybersos.domain import AccessField, FactValue, Incident, Provider
from cybersos.domain.frozen_values import freeze
from cybersos.playbooks.source_registry import OFFICIAL_DESTINATIONS


class RiskLevel(StrEnum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'


class SimulationEffect(StrEnum):
    ATTEMPT_PROVIDER_VERIFICATION = 'attempt_provider_verification'
    RECOVERY_ATTEMPT = 'recovery_attempt'
    PROTECTIVE_STEP = 'protective_step'
    PROVIDER_ADMIN_HANDOFF = 'provider_admin_handoff'
    ERASE_DEVICE = 'erase_device'


@dataclass(frozen=True)
class Source:
    id: str
    url: str
    title: str
    scope: tuple[Provider, ...]
    checked_on: date


@dataclass(frozen=True)
class RecoveryRule:
    id: str
    provider: Provider
    incident: tuple[Incident, ...]
    source_ids: tuple[str, ...]
    checked_on: date
    requires: Mapping[AccessField, FactValue]
    scope_note: str
    unknown_requires_question: bool
    user_instruction: str
    simulation_effect: SimulationEffect
    real_account_effect: str
    risk_level: RiskLevel
    review_status: str = 'source_checked'

    def __post_init__(self) -> None:
        object.__setattr__(self, 'requires', freeze(dict(self.requires)))


@dataclass(frozen=True)
class PlaybookRegistry:
    sources: Mapping[str, Source]
    rules: Mapping[str, RecoveryRule]

    def __post_init__(self) -> None:
        object.__setattr__(self, 'sources', freeze(dict(self.sources)))
        object.__setattr__(self, 'rules', freeze(dict(self.rules)))

    def lookup(self, provider: Provider, incident: Incident,
               rule_id: str | None = None) -> tuple[RecoveryRule, ...]:
        return tuple(rule for rule in self.rules.values()
                     if rule.provider == provider and incident in rule.incident
                     and (rule_id is None or rule.id == rule_id))

    def destinations(self, source_ids: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(OFFICIAL_DESTINATIONS[source_id] for source_id in source_ids)
