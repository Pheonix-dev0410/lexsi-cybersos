from cybersos.domain import Action, TerminalState, ToolName
from cybersos.safety import GuardVerdict, guard_action
from cybersos.simulator.episode_state import EpisodeState
from cybersos.simulator.observations import ActionObservation
from cybersos.simulator.scripted_event_effects import apply_corrections, temporary_failure
from cybersos.simulator.tool_dispatch import dispatch_tool
from cybersos.simulator.tool_results import ToolResult


def execute_action(state: EpisodeState, action: Action) -> ToolResult:
    if not state.accepting_actions:
        return ToolResult(action.tool_name, False, {}, 'Episode ended or awaiting a user report')
    verdict = guard_action(action, state.guard_context())
    if not verdict.allowed:
        return record_blocked_action(state, action, verdict)
    state.action_count += 1
    result = temporary_failure(state, action) or dispatch_tool(state, action)
    state.record_turn(ActionObservation(action, verdict, result, state.pending_proposal))
    state.log('tool_result', {'tool_name': action.tool_name.value, 'ok': result.ok,
                              'data': result.data})
    apply_corrections(state, action, result)
    state.settle_budget()
    return result


def record_blocked_action(state: EpisodeState, action: Action | None,
                          verdict: GuardVerdict) -> ToolResult:
    name = action.tool_name if action else ToolName.FINISH
    result = ToolResult(name, False, {'violations': tuple(v.kind.value for v in verdict.violations)},
                        'Proposal blocked')
    if not state.accepting_actions:
        return result
    state.action_count += 1
    state.log('guard_blocked', {'violations': tuple(
        {'kind': v.kind.value, 'critical': v.critical} for v in verdict.violations)})
    if action and action.tool_name == ToolName.FINISH:
        state.log('finish_proposed', dict(action.parameters))
        state.terminal = TerminalState.INVALID_FINISH
    state.record_turn(ActionObservation(action, verdict, result, state.pending_proposal))
    state.settle_budget()
    return result
