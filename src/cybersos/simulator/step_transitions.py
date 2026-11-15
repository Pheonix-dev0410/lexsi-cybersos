from cybersos.domain import (
    AccessField, Availability, FactSource, ProviderResponse, SessionMode, ToolName,
)
from cybersos.playbooks import PlaybookRegistry, RecoveryRule, SimulationEffect
from cybersos.simulator.episode_state import EpisodeState
from cybersos.simulator.step_evidence import step_evidence
from cybersos.simulator.tool_results import ToolResult


_ERASED_DEVICE_FACTS = (
    (AccessField.DEVICE_ERASED, Availability.TRUE), (AccessField.PHONE_AVAILABLE, Availability.FALSE),
    (AccessField.DEVICE_SIGNED_IN, Availability.FALSE), (AccessField.FIND_HUB_ENABLED, Availability.FALSE),
)


def render_step(registry: PlaybookRegistry, rule: RecoveryRule) -> dict[str, object]:
    return {'step_id': rule.id, 'instruction': rule.user_instruction,
            'source_ids': rule.source_ids, 'urls': registry.destinations(rule.source_ids),
            'scope_note': rule.scope_note}


def _observed_response(rule: RecoveryRule, scripted: ProviderResponse) -> ProviderResponse:
    if rule.simulation_effect == SimulationEffect.PROVIDER_ADMIN_HANDOFF:
        return ProviderResponse.SUCCESS
    if rule.simulation_effect == SimulationEffect.RECOVERY_ATTEMPT and scripted == ProviderResponse.SUCCESS:
        return ProviderResponse.PENDING_REVIEW
    return scripted


def transition_step(state: EpisodeState, rule: RecoveryRule) -> ToolResult:
    state.attempted.add(rule.id)
    data = render_step(state.registry, rule)
    if state.mode == SessionMode.INCIDENT_GUIDANCE:
        state.pending_step = rule.id
        data.update({'evidence_basis': 'guidance_only', 'awaiting': 'user_report'})
        return ToolResult(ToolName.SIMULATE_STEP, True, data, paused=True)
    response = _observed_response(rule, state.provider.respond(state.scenario, rule))
    completed, terminals = step_evidence(rule, response)
    state.add_evidence(terminals, rule.id)
    if completed:
        state.completed.add(rule.id)
        _apply_provider_effect(state, rule)
    if response == ProviderResponse.DENIAL:
        state.record_fact(AccessField.REAUTHENTICATION_AVAILABLE, Availability.FALSE,
                          FactSource.PROVIDER_EVENT, True)
    data.update({'provider_response': response.value, 'evidence_basis': 'simulated_provider'})
    state.log('provider_response', {'step_id': rule.id, 'response': response.value})
    return ToolResult(ToolName.SIMULATE_STEP, True, data)


def _apply_provider_effect(state: EpisodeState, rule: RecoveryRule) -> None:
    if rule.simulation_effect == SimulationEffect.ATTEMPT_PROVIDER_VERIFICATION:
        state.verified_access = True
        for field in (AccessField.ACCOUNT_ACCESS_AVAILABLE, AccessField.REAUTHENTICATION_AVAILABLE):
            state.record_fact(field, Availability.TRUE, FactSource.PROVIDER_EVENT, True)
    if rule.simulation_effect == SimulationEffect.ERASE_DEVICE:
        for field, value in _ERASED_DEVICE_FACTS:
            state.record_fact(field, value, FactSource.PROVIDER_EVENT, True)
