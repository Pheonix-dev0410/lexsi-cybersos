from typing import NamedTuple

from cybersos.domain import ProviderResponse, TerminalState
from cybersos.playbooks import RecoveryRule, SimulationEffect


class StepEvidence(NamedTuple):
    completed: bool
    terminals: frozenset[TerminalState]


def step_evidence(rule: RecoveryRule, response: ProviderResponse | str) -> StepEvidence:
    """Evidence from a step's observed response, after the simulator applied the rule's effect.

    A handoff is evidence of a handoff whatever the provider says, and an official
    recovery submission is pending review even when accepted; neither completes the step.
    """
    response = ProviderResponse(response)
    effect = rule.simulation_effect
    if effect == SimulationEffect.PROVIDER_ADMIN_HANDOFF:
        return StepEvidence(False, frozenset({TerminalState.NEEDS_PROVIDER_OR_ADMIN}))
    if response == ProviderResponse.PENDING_REVIEW or (
            effect == SimulationEffect.RECOVERY_ATTEMPT and response == ProviderResponse.SUCCESS):
        return StepEvidence(False, frozenset({TerminalState.OFFICIAL_RECOVERY_PENDING}))
    if response != ProviderResponse.SUCCESS:
        return StepEvidence(False, frozenset())
    if effect == SimulationEffect.ATTEMPT_PROVIDER_VERIFICATION:
        return StepEvidence(True, frozenset({TerminalState.SIMULATED_ACCESS_RESTORED}))
    return StepEvidence(True, frozenset())


def user_reported_evidence(rule: RecoveryRule, response: ProviderResponse | str) -> frozenset[TerminalState]:
    """A person's report can support a handoff or pending recovery, never a verified restoration."""
    return step_evidence(rule, response).terminals - {TerminalState.SIMULATED_ACCESS_RESTORED}
