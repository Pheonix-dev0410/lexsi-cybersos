from dataclasses import dataclass
from enum import StrEnum

from cybersos.domain import AccessField, Availability, ObservedFacts
from cybersos.domain.factor_availability import effective_access_value
from cybersos.playbooks.rules import RecoveryRule


class Readiness(StrEnum):
    READY = 'ready'
    BLOCKED = 'blocked'
    NEEDS_INFORMATION = 'needs_information'


@dataclass(frozen=True)
class PrerequisiteResult:
    status: Readiness
    blocked_fields: tuple[AccessField, ...]
    unknown_fields: tuple[AccessField, ...]
    revision: int


def evaluate_prerequisites(rule: RecoveryRule, facts: ObservedFacts) -> PrerequisiteResult:
    """Evaluate disclosed facts only, including disclosed factor dependencies."""
    blocked: list[AccessField] = []
    unknown: list[AccessField] = []
    for field, expected in rule.requires.items():
        actual = effective_access_value(field, facts.value)
        if actual == Availability.UNKNOWN:
            unknown.append(field)
        elif actual != expected:
            blocked.append(field)
    status = Readiness.BLOCKED if blocked else (
        Readiness.NEEDS_INFORMATION if unknown else Readiness.READY)
    return PrerequisiteResult(status, tuple(blocked), tuple(unknown), facts.revision)
