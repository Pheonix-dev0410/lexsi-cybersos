from dataclasses import dataclass, field

from cybersos.domain import (
    AccessField, ExecutionStatus, FactSource, FactValue, ObservedFacts, Scenario, SessionMode,
    TerminalState,
)
from cybersos.playbooks import PlaybookRegistry
from cybersos.safety import GuardContext
from cybersos.simulator.observations import ActionObservation
from cybersos.simulator.provider_responder import ScriptedProvider
from cybersos.simulator.terminal_support import supported_conclusions
from cybersos.simulator.tool_results import ToolResult
from cybersos.simulator.trusted_snapshot import Event


@dataclass
class EpisodeState:
    """Mutable server-side state of one episode, owned by its `RecoveryEnvironment`."""

    scenario: Scenario
    registry: PlaybookRegistry
    mode: SessionMode
    action_budget: int
    facts: ObservedFacts = field(default_factory=ObservedFacts)
    access_state: dict[AccessField, FactValue] = field(default_factory=dict)
    answer_overrides: dict[AccessField, FactValue] = field(default_factory=dict)
    events: list[Event] = field(default_factory=list)
    history: list[ToolResult] = field(default_factory=list)
    action_history: list[ActionObservation] = field(default_factory=list)
    provider: ScriptedProvider = field(default_factory=ScriptedProvider)
    attempted: set[str] = field(default_factory=set)
    completed: set[str] = field(default_factory=set)
    applied_corrections: set[int] = field(default_factory=set)
    failed_once: set[int] = field(default_factory=set)
    user_reported_successes: set[str] = field(default_factory=set)
    evidence: dict[TerminalState, set[str]] = field(default_factory=dict)
    verified_access: bool = False
    halted: bool = False
    execution_status: ExecutionStatus | None = None
    terminal: TerminalState | None = None
    action_count: int = 0
    pending_proposal: str | None = None
    pending_step: str | None = None
    pending_field: AccessField | None = None

    @property
    def done(self) -> bool:
        return self.halted or self.terminal is not None

    @property
    def awaiting_report(self) -> bool:
        return self.pending_step is not None or self.pending_field is not None

    @property
    def accepting_actions(self) -> bool:
        return not self.done and not self.awaiting_report

    def guard_context(self) -> GuardContext:
        scenario = self.scenario
        attempted = frozenset(self.attempted)
        supported = supported_conclusions(
            self.registry, self.facts, scenario.provider, scenario.incident, self.evidence,
            self.completed, scenario.required_protective_steps,
            opening_message=scenario.opening_message, attempted=attempted)
        return GuardContext(self.registry, scenario.provider, scenario.incident,
                            ObservedFacts.from_history(self.facts.history), scenario.permissions,
                            self.mode, attempted, supported,
                            {terminal: frozenset(steps) for terminal, steps in self.evidence.items()},
                            scenario.opening_message)

    def log(self, kind: str, data: dict[str, object]) -> None:
        self.events.append(Event(len(self.events) + 1, kind, data))

    def record_fact(self, field_name: AccessField, value: object, source: FactSource,
                    correction: bool) -> None:
        fact = self.facts.record(field_name, value, source, correction=correction)
        if source == FactSource.PROVIDER_EVENT:
            self.access_state[fact.field] = fact.value
            self.answer_overrides[fact.field] = fact.value
        self.log('fact_recorded', {'field': fact.field.value, 'value': fact.value.value,
                                   'source': fact.source.value, 'revision': fact.revision,
                                   'correction': correction, 'conflicted': fact.conflicted,
                                   'reported_value': fact.reported_value.value})

    def add_evidence(self, terminals: frozenset[TerminalState], step_id: str) -> None:
        for terminal in terminals:
            self.evidence.setdefault(terminal, set()).add(step_id)

    def record_turn(self, turn: ActionObservation) -> None:
        self.history.append(turn.result)
        self.action_history.append(turn)
        self.pending_proposal = None

    def end_on_user_report(self, terminal: TerminalState | None) -> None:
        """End an incident session the person says is complete; nothing is independently verified."""
        self.halted = True
        self.execution_status = ExecutionStatus.FINISHED
        self.terminal = terminal
        self.log('user_reported_completion',
                 {'terminal_state': terminal.value if terminal else None})

    def exhaust_budget(self) -> None:
        if not self.done:
            self.terminal = TerminalState.BUDGET_EXHAUSTED
            self.pending_step = None
            self.pending_field = None
            self.log('budget_exhausted', {})

    def settle_budget(self) -> None:
        if self.action_count >= self.action_budget and self.accepting_actions:
            self.exhaust_budget()
