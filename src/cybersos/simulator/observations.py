from dataclasses import dataclass

from cybersos.domain import Action, Fact, ObservedFacts, SessionMode
from cybersos.safety.violations import GuardVerdict
from cybersos.simulator.tool_results import ToolResult


@dataclass(frozen=True)
class ActionObservation:
    action: Action | None
    guard_verdict: GuardVerdict
    result: ToolResult
    raw_proposal: str | None = None


@dataclass(frozen=True)
class Observation:
    provider: str
    incident: str
    mode: SessionMode
    opening_message: str
    facts: tuple[Fact, ...]
    history: tuple[ToolResult, ...]
    actions_remaining: int
    done: bool
    awaiting_report: bool
    observation_mode: str = 'structured'
    fact_history: tuple[Fact, ...] = ()
    action_history: tuple[ActionObservation, ...] = ()

    @property
    def observed_facts(self) -> 'ObservedFacts':
        return ObservedFacts.from_history(self.fact_history or self.facts)
