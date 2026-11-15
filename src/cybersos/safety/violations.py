from dataclasses import dataclass
from enum import StrEnum


class ViolationKind(StrEnum):
    INVALID_PROPOSAL = 'invalid_proposal'
    UNAVAILABLE_PREREQUISITE = 'unavailable_prerequisite'
    SECRET_SOLICITATION = 'secret_solicitation'
    UNAUTHORIZED_ASSISTANCE = 'unauthorized_assistance'
    UNAPPROVED_DESTRUCTIVE_ACTION = 'unapproved_destructive_action'
    FABRICATED_DESTINATION_OR_EVIDENCE = 'fabricated_destination_or_evidence'
    FALSE_COMPLETION = 'false_completion'


@dataclass(frozen=True)
class Violation:
    kind: ViolationKind
    detail: str

    @property
    def critical(self) -> bool:
        return self.kind not in {ViolationKind.INVALID_PROPOSAL,
                                 ViolationKind.UNAVAILABLE_PREREQUISITE}


@dataclass(frozen=True)
class GuardVerdict:
    allowed: bool
    violations: tuple[Violation, ...] = ()
