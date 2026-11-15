from dataclasses import dataclass

from cybersos.domain import Action, ExecutionStatus, SessionMode, TaskOutcome, TerminalState
from cybersos.safety import GuardVerdict
from cybersos.simulator import Event, ToolResult


@dataclass(frozen=True)
class DecisionTrace:
    turn: int
    raw_proposal: str
    action: Action | None
    parse_error: str | None
    guard_verdict: GuardVerdict
    tool_result: ToolResult


@dataclass(frozen=True)
class EpisodeTrace:
    episode_id: str
    scenario_id: str
    mode: SessionMode
    decisions: tuple[DecisionTrace, ...]
    events: tuple[Event, ...]
    terminal_state: TerminalState | None
    execution_status: ExecutionStatus | None
    outcome: TaskOutcome
    paused: bool = False
    error: str | None = None
    observation_mode: str = 'structured'

    @property
    def unsafe_proposal_count(self) -> int:
        return sum(any(v.critical for v in decision.guard_verdict.violations)
                   for decision in self.decisions)
