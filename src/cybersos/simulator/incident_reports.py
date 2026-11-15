from dataclasses import replace

from cybersos.domain import (
    AccessField, Availability, FactSource, Provider, ProviderResponse, SessionMode,
    TerminalState, ToolName,
)
from cybersos.domain.access import normalize_value
from cybersos.playbooks import SimulationEffect
from cybersos.simulator.episode_state import EpisodeState
from cybersos.simulator.step_evidence import user_reported_evidence
from cybersos.simulator.tool_results import ToolResult


def report_access(state: EpisodeState, value: object, *, correction: bool) -> None:
    if state.done or state.mode != SessionMode.INCIDENT_GUIDANCE or state.pending_field is None:
        raise ValueError('No incident access question is pending')
    field = state.pending_field
    state.record_fact(field, normalize_value(field, value), FactSource.USER_REPORTED, correction)
    state.pending_field = None
    result = ToolResult(ToolName.ASK_ACCESS, True, {'field': field.value,
                        'value': state.facts.value(field).value, 'evidence_basis': 'user_reported'})
    _resolve_pending_turn(state, result)


def report_step(state: EpisodeState, response: ProviderResponse) -> ToolResult:
    if state.done or state.mode != SessionMode.INCIDENT_GUIDANCE or state.pending_step is None:
        raise ValueError('No incident step is pending')
    response = ProviderResponse(response)
    step_id = state.pending_step
    rule = state.registry.rules[step_id]
    if response == ProviderResponse.DENIAL:
        state.record_fact(AccessField.REAUTHENTICATION_AVAILABLE, Availability.FALSE,
                          FactSource.USER_REPORTED, True)
    if (response == ProviderResponse.SUCCESS and
            rule.simulation_effect == SimulationEffect.ATTEMPT_PROVIDER_VERIFICATION):
        state.record_fact(AccessField.ACCOUNT_ACCESS_AVAILABLE, Availability.TRUE,
                          FactSource.USER_REPORTED, True)
    state.add_evidence(user_reported_evidence(rule, response), step_id)
    state.pending_step = None
    result = ToolResult(ToolName.SIMULATE_STEP, True, {'step_id': step_id,
                        'reported_response': response.value, 'evidence_basis': 'user_reported',
                        'verified_access_restored': False})
    state.log('user_report', dict(result.data))
    _resolve_pending_turn(state, result)
    if response == ProviderResponse.SUCCESS:
        state.user_reported_successes.add(step_id)
        _end_if_reported_complete(state, rule.simulation_effect)
    return result


def _end_if_reported_complete(state: EpisodeState, effect: SimulationEffect) -> None:
    required = state.scenario.required_protective_steps
    if effect == SimulationEffect.ATTEMPT_PROVIDER_VERIFICATION and not required:
        # A person regaining access is their report, so no restoration terminal is claimed.
        state.end_on_user_report(None)
    elif effect == SimulationEffect.PROTECTIVE_STEP and (
            state.scenario.provider == Provider.ANDROID
            or set(required) <= state.user_reported_successes):
        state.end_on_user_report(TerminalState.PROTECTIVE_WORKFLOW_COMPLETED)


def _resolve_pending_turn(state: EpisodeState, result: ToolResult) -> None:
    state.history.append(result)
    state.action_history[-1] = replace(state.action_history[-1], result=result)
    state.settle_budget()
