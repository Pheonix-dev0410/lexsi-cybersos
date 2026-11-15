from dataclasses import dataclass
from typing import Mapping

from cybersos.domain import Fact, TerminalState
from cybersos.domain.frozen_values import freeze


@dataclass(frozen=True)
class Event:
    sequence: int
    kind: str
    data: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, 'data', freeze(dict(self.data)))


@dataclass(frozen=True)
class TrustedSnapshot:
    scenario_id: str
    hidden_access: Mapping[str, object]
    provider_script: Mapping[str, object]
    facts: tuple[Fact, ...]
    events: tuple[Event, ...]
    attempted_steps: frozenset[str]
    completed_steps: frozenset[str]
    verified_access_restored: bool
    terminal_state: TerminalState | None
    action_count: int
    done: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, 'hidden_access', freeze(dict(self.hidden_access)))
        object.__setattr__(self, 'provider_script', freeze(dict(self.provider_script)))
