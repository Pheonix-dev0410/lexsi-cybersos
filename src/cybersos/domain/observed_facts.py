from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping

from cybersos.domain.access import AccessField, Availability, FactValue, normalize_value


class FactSource(StrEnum):
    INTAKE = 'intake'
    SCRIPTED_ANSWER = 'scripted_answer'
    USER_REPORTED = 'user_reported'
    PROVIDER_EVENT = 'provider_event'


@dataclass(frozen=True)
class Fact:
    field: AccessField
    value: FactValue
    source: FactSource
    revision: int
    correction: bool = False
    conflicted: bool = False
    reported_value: FactValue | None = None


class ObservedFacts:
    def __init__(self) -> None:
        self._history: list[Fact] = []
        self._active: dict[AccessField, Fact] = {}

    @property
    def revision(self) -> int:
        return len(self._history)

    @property
    def history(self) -> tuple[Fact, ...]:
        return tuple(self._history)

    def value(self, field: AccessField | str) -> FactValue:
        fact = self._active.get(AccessField(field))
        return fact.value if fact else Availability.UNKNOWN

    def record(self, field: AccessField | str, value: object, source: FactSource,
               *, correction: bool = False) -> Fact:
        field = AccessField(field)
        normalized = normalize_value(field, value)
        previous = self._active.get(field)
        conflict = bool(previous and not correction and
                        (previous.conflicted or (previous.value != normalized and
                         previous.value != Availability.UNKNOWN)))
        fact = Fact(field, Availability.UNKNOWN if conflict else normalized,
                    FactSource(source), self.revision + 1, correction, conflict, normalized)
        self._history.append(fact)
        self._active[field] = fact
        return fact

    def snapshot(self) -> tuple[Fact, ...]:
        return tuple(self._active.values())

    def as_dict(self) -> dict[str, object]:
        return {fact.field.value: {'value': fact.value.value, 'source': fact.source.value,
                                  'revision': fact.revision, 'conflicted': fact.conflicted}
                for fact in self.snapshot()}

    @classmethod
    def from_history(cls, history: tuple[Fact, ...]) -> 'ObservedFacts':
        facts = cls()
        for fact in history:
            facts.record(fact.field, fact.reported_value or fact.value, fact.source,
                         correction=fact.correction)
        return facts

    @classmethod
    def from_mapping(cls, values: Mapping[str | AccessField, object],
                     source: FactSource = FactSource.INTAKE) -> 'ObservedFacts':
        facts = cls()
        for field, value in values.items():
            facts.record(field, value, source)
        return facts
