from cybersos.domain import AccessField, Action, Incident, Provider, TerminalState, ToolName
from cybersos.simulator.environment import RecoveryEnvironment
from cybersos.simulator.tool_results import ToolResult


class EpisodeTools:
    def __init__(self, environment: RecoveryEnvironment) -> None:
        self._environment = environment

    def ask_access(self, field: AccessField) -> ToolResult:
        """Ask only for availability of the enum field, never a secret value."""
        return self._environment.execute(Action(ToolName.ASK_ACCESS, {'field': field}))

    def lookup_playbook(self, provider: Provider, incident: Incident,
                        rule_id: str | None = None) -> ToolResult:
        """Retrieve authored context for this scope, optionally selecting one rule ID."""
        params: dict[str, object] = {'provider': provider, 'incident': incident}
        if rule_id is not None:
            params['rule_id'] = rule_id
        return self._environment.execute(Action(ToolName.LOOKUP_PLAYBOOK, params))

    def check_step(self, step_id: str) -> ToolResult:
        """Recheck a registered step using only currently disclosed facts."""
        return self._environment.execute(Action(ToolName.CHECK_STEP, {'step_id': step_id}))

    def simulate_step(self, step_id: str, confirmation: bool | None = None) -> ToolResult:
        """Attempt a step; confirmation is required for permitted benchmark erasure."""
        params: dict[str, object] = {'step_id': step_id}
        if confirmation is not None:
            params['confirmation'] = confirmation
        return self._environment.execute(Action(ToolName.SIMULATE_STEP, params))

    def finish(self, status: TerminalState, next_step_id: str | None,
               source_ids: tuple[str, ...]) -> ToolResult:
        """Propose a conclusion with registered evidence; the server decides support."""
        return self._environment.execute(Action(ToolName.FINISH, {
            'status': status, 'next_step_id': next_step_id, 'source_ids': source_ids}))
