from collections.abc import Mapping

from cybersos.domain import AccessField, Action, FactSource, SessionMode, TerminalState, ToolName
from cybersos.playbooks import evaluate_prerequisites
from cybersos.simulator.access_responder import scripted_access_answer
from cybersos.simulator.episode_state import EpisodeState
from cybersos.simulator.step_transitions import render_step, transition_step
from cybersos.simulator.tool_results import ToolResult


def dispatch_tool(state: EpisodeState, action: Action) -> ToolResult:
    params = action.parameters
    if action.tool_name == ToolName.ASK_ACCESS:
        return _ask_access(state, AccessField(params['field']))
    if action.tool_name == ToolName.LOOKUP_PLAYBOOK:
        return _lookup_playbook(state, params)
    if action.tool_name == ToolName.CHECK_STEP:
        return _check_step(state, str(params['step_id']))
    if action.tool_name == ToolName.SIMULATE_STEP:
        return transition_step(state, state.registry.rules[params['step_id']])
    status = TerminalState(params['status'])
    state.log('finish_proposed', dict(params))
    state.terminal = status
    return ToolResult(action.tool_name, True, {'terminal_state': status.value,
                                               'verified_access_restored': state.verified_access})


def _ask_access(state: EpisodeState, field: AccessField) -> ToolResult:
    if state.mode == SessionMode.INCIDENT_GUIDANCE:
        state.pending_field = field
        return ToolResult(ToolName.ASK_ACCESS, True, {'field': field.value, 'awaiting': 'user_answer'},
                          paused=True)
    value = scripted_access_answer(state.scenario, field, access_state=state.access_state,
                                   answer_overrides=state.answer_overrides)
    state.record_fact(field, value, FactSource.SCRIPTED_ANSWER, False)
    return ToolResult(ToolName.ASK_ACCESS, True, {'field': field.value,
                                                  'value': state.facts.value(field).value})


def _lookup_playbook(state: EpisodeState, params: Mapping[str, object]) -> ToolResult:
    rules = state.registry.lookup(state.scenario.provider, state.scenario.incident, params.get('rule_id'))
    return ToolResult(ToolName.LOOKUP_PLAYBOOK, True, {'rules': tuple(render_step(state.registry, rule) | {
        'requires': {field.value: value.value for field, value in rule.requires.items()},
        'checked_on': rule.checked_on.isoformat(),
        'unknown_requires_question': rule.unknown_requires_question,
        'real_account_effect': rule.real_account_effect,
        'risk_level': rule.risk_level.value, 'simulation_effect': rule.simulation_effect.value,
        'review_status': rule.review_status} for rule in rules)})


def _check_step(state: EpisodeState, step_id: str) -> ToolResult:
    result = evaluate_prerequisites(state.registry.rules[step_id], state.facts)
    status = 'blocked' if step_id in state.attempted else result.status.value
    return ToolResult(ToolName.CHECK_STEP, True, {
        'step_id': step_id, 'status': status,
        'blocked_fields': tuple(field.value for field in result.blocked_fields),
        'unknown_fields': tuple(field.value for field in result.unknown_fields),
        'revision': result.revision})
