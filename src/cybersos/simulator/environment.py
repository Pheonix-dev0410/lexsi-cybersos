from cybersos.domain import (
    AccessField, Action, ExecutionStatus, FactSource, ProviderResponse, Scenario, SessionMode,
    TaskOutcome, TerminalState,
)
from cybersos.playbooks import PlaybookRegistry
from cybersos.safety import GuardContext, GuardVerdict
from cybersos.simulator.action_execution import execute_action, record_blocked_action
from cybersos.simulator.episode_state import EpisodeState
from cybersos.simulator.incident_reports import report_access, report_step
from cybersos.simulator.observations import Observation
from cybersos.simulator.tool_results import ToolResult
from cybersos.simulator.trusted_snapshot import TrustedSnapshot


class RecoveryEnvironment:
    def __init__(self, scenario: Scenario, registry: PlaybookRegistry, *, episode_id: str,
                 mode: SessionMode = SessionMode.BENCHMARK, action_budget: int = 12) -> None:
        if not 1 <= action_budget <= 12:
            raise ValueError('Action budget must be between 1 and 12')
        self.episode_id = episode_id
        self._state = EpisodeState(scenario, registry, SessionMode(mode), action_budget,
                                   access_state=dict(scenario.access),
                                   answer_overrides=dict(scenario.access_answers))
        for field, value in scenario.initial_facts.items():
            self._state.record_fact(field, value, FactSource.INTAKE, False)

    @property
    def registry(self) -> PlaybookRegistry:
        return self._state.registry

    @property
    def mode(self) -> SessionMode:
        return self._state.mode

    @property
    def action_budget(self) -> int:
        return self._state.action_budget

    @property
    def scenario_id(self) -> str:
        return self._state.scenario.scenario_id

    @property
    def done(self) -> bool:
        return self._state.done

    @property
    def awaiting_report(self) -> bool:
        return self._state.awaiting_report

    @property
    def terminal_state(self) -> TerminalState | None:
        return self._state.terminal

    @property
    def execution_status(self) -> ExecutionStatus | None:
        state = self._state
        if state.execution_status is not None:
            return state.execution_status
        if state.terminal == TerminalState.ENVIRONMENT_ERROR:
            return ExecutionStatus.ENVIRONMENT_ERROR
        return ExecutionStatus.FINISHED if state.done else None

    def observation(self) -> Observation:
        state = self._state
        return Observation(state.scenario.provider.value, state.scenario.incident.value, state.mode,
                           state.scenario.opening_message, state.facts.snapshot(), tuple(state.history),
                           state.action_budget - state.action_count, state.done, state.awaiting_report,
                           fact_history=state.facts.history, action_history=tuple(state.action_history))

    def guard_context(self) -> GuardContext:
        return self._state.guard_context()

    def execute(self, action: Action) -> ToolResult:
        return execute_action(self._state, action)

    def record_raw_proposal(self, raw_text: str) -> None:
        if self._state.accepting_actions:
            self._state.pending_proposal = raw_text
            self._state.log('raw_proposal', {'raw_text': raw_text})

    def record_guard_verdict(self, verdict: GuardVerdict) -> None:
        if self._state.accepting_actions:
            self._state.log('guard_verdict', {'allowed': verdict.allowed, 'violations': tuple(
                {'kind': v.kind.value, 'critical': v.critical} for v in verdict.violations)})

    def record_blocked_action(self, action: Action | None, verdict: GuardVerdict) -> ToolResult:
        return record_blocked_action(self._state, action, verdict)

    def end_execution(self, status: ExecutionStatus) -> None:
        state = self._state
        if state.done:
            return
        if status == ExecutionStatus.ENVIRONMENT_ERROR:
            state.terminal = TerminalState.ENVIRONMENT_ERROR
        state.halted = True
        state.execution_status = ExecutionStatus(status)
        state.pending_step = None
        state.pending_field = None
        state.log('execution_ended', {'execution_status': status.value})

    def exhaust_budget(self) -> None:
        self._state.exhaust_budget()

    def task_outcome(self) -> TaskOutcome:
        terminal = self._state.terminal
        if (self.mode == SessionMode.INCIDENT_GUIDANCE or terminal is None or
                terminal == TerminalState.ENVIRONMENT_ERROR):
            return TaskOutcome.INDETERMINATE
        objective = self._state.scenario.objective
        failures = {TerminalState.BUDGET_EXHAUSTED, TerminalState.INVALID_FINISH}
        met = terminal not in failures and (objective is None or terminal == objective)
        return TaskOutcome.OBJECTIVE_MET if met else TaskOutcome.OBJECTIVE_NOT_MET

    def trusted_snapshot(self) -> TrustedSnapshot:
        state = self._state
        return TrustedSnapshot(state.scenario.scenario_id, {
            **{key.value: value.value for key, value in state.access_state.items()},
            'account_owner': state.scenario.account_owner}, state.scenario.provider_script,
            state.facts.history, tuple(state.events), frozenset(state.attempted),
            frozenset(state.completed), state.verified_access, state.terminal, state.action_count,
            state.done)

    def update_fact(self, field: AccessField, value: object, *,
                    source: FactSource = FactSource.USER_REPORTED, correction: bool = False) -> None:
        """Trusted intake hook; model actions cannot submit authoritative facts."""
        if not self._state.accepting_actions:
            raise ValueError('Episode ended or awaiting a specific report')
        self._state.record_fact(field, value, source, correction)

    def report_access(self, value: object, *, correction: bool = False) -> None:
        report_access(self._state, value, correction=correction)

    def report_step(self, response: ProviderResponse) -> ToolResult:
        return report_step(self._state, response)
