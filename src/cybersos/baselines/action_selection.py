from cybersos.domain import Action, Incident, Provider, TerminalState
from cybersos.playbooks import PlaybookRegistry, RecoveryRule, SimulationEffect, finish_action
from cybersos.simulator import Observation, ObservedProgress, supported_conclusions


ROUTE_ORDER = (
    'managed_account_boundary', 'child_account_boundary', 'use_independent_passkey',
    'use_accessible_backup_code', 'use_security_key', 'use_alternate_number',
    'use_available_phone', 'use_trusted_session', 'secure_android_device',
    'official_account_recovery', 'android_account_recovery',
)


def supported_finish(observation: Observation, registry: PlaybookRegistry,
                     progress: ObservedProgress, required_steps: tuple[str, ...]) -> Action | None:
    supported = supported_conclusions(
        registry, observation.observed_facts, Provider(observation.provider),
        Incident(observation.incident), progress.evidence, progress.completed, required_steps,
        opening_message=observation.opening_message, attempted=progress.attempted)
    for terminal in (TerminalState.UNSAFE_REQUEST_DECLINED,
                     TerminalState.PROTECTIVE_WORKFLOW_COMPLETED,
                     TerminalState.SIMULATED_ACCESS_RESTORED, TerminalState.NEEDS_PROVIDER_OR_ADMIN,
                     TerminalState.OFFICIAL_RECOVERY_PENDING, TerminalState.NO_SUPPORTED_PATH_KNOWN):
        if terminal not in supported:
            continue
        if terminal == TerminalState.SIMULATED_ACCESS_RESTORED and required_steps:
            continue
        steps = progress.evidence.get(terminal, frozenset())
        return finish_action(terminal, registry, min(steps) if steps else None)
    return None


def ordered_routes(observation: Observation, registry: PlaybookRegistry,
                   progress: ObservedProgress, required_steps: tuple[str, ...]) -> list[RecoveryRule]:
    rules = [rule for rule in registry.lookup(Provider(observation.provider), Incident(observation.incident))
             if rule.id not in progress.attempted and
             rule.simulation_effect != SimulationEffect.ERASE_DEVICE]

    def order(rule: RecoveryRule) -> tuple[int, int]:
        if rule.id in required_steps:
            return (0, required_steps.index(rule.id))
        return (1, ROUTE_ORDER.index(rule.id) if rule.id in ROUTE_ORDER else len(ROUTE_ORDER))

    return sorted(rules, key=order)
