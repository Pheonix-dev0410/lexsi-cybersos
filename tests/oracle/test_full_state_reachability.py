from dataclasses import replace

from cybersos.data.diagnostic_scenarios import load_diagnostic_scenarios
from cybersos.domain import Scenario, TemporaryToolFailure, TerminalState, ToolName
from cybersos.oracle import reachable_routes, reference_trajectory, safe_resolution
from cybersos.playbooks import PlaybookRegistry
from cybersos.project_paths import DIAGNOSTIC_CASES_PATH
from cybersos.simulator import RecoveryEnvironment


def backup_scenario() -> Scenario:
    cases = load_diagnostic_scenarios(DIAGNOSTIC_CASES_PATH)
    return next(c.scenario for c in cases if c.scenario.scenario_id == 'paper_backup_saved')


def test_circular_backup_storage_cannot_restore_access(registry: PlaybookRegistry) -> None:
    scenario = backup_scenario()
    independent = reachable_routes(scenario, registry)
    circular = replace(scenario, access=dict(scenario.access) | {'backup_code_storage': 'same_locked_account'},
                       initial_facts={})
    assert independent.reaches(TerminalState.SIMULATED_ACCESS_RESTORED)
    assert not reachable_routes(circular, registry).reaches(TerminalState.SIMULATED_ACCESS_RESTORED)


def test_multiple_valid_routes_are_accepted(registry: PlaybookRegistry) -> None:
    scenario = backup_scenario()
    scenario = replace(scenario, access=dict(scenario.access) | {
        'independent_passkey_exists': True, 'independent_passkey_available': True},
        provider_script={'use_accessible_backup_code': 'success', 'use_independent_passkey': 'success'})
    paths = {route.step_ids for route in reachable_routes(scenario, registry).routes
             if route.terminal_state == TerminalState.SIMULATED_ACCESS_RESTORED}
    assert ('use_accessible_backup_code',) in paths
    assert ('use_independent_passkey',) in paths


def test_reference_asks_before_using_hidden_available_factor(registry: PlaybookRegistry) -> None:
    scenario = backup_scenario()
    trace = reference_trajectory(scenario, registry)
    assert trace.decisions[0].action.tool_name == ToolName.ASK_ACCESS
    assert trace.decisions[0].action.parameters['field'] == 'backup_code_accessible_now'
    assert safe_resolution(trace, scenario, registry)
    assert not any('provider_script' in d.raw_proposal for d in trace.decisions)
    assert RecoveryEnvironment(scenario, registry, episode_id='fresh').trusted_snapshot().action_count == 0


def test_pending_review_is_not_reachable_restoration(registry: PlaybookRegistry) -> None:
    scenario = replace(backup_scenario(), provider_script={
        'use_accessible_backup_code': 'pending_review', 'official_account_recovery': 'success'})
    result = reachable_routes(scenario, registry)
    assert result.reaches(TerminalState.OFFICIAL_RECOVERY_PENDING)
    assert not result.reaches(TerminalState.SIMULATED_ACCESS_RESTORED)


def test_failed_route_can_unlock_later_effect_script_success(registry: PlaybookRegistry) -> None:
    scenario = backup_scenario()
    scenario = replace(scenario, access=dict(scenario.access) | {
        'enrolled_security_key_exists': True, 'enrolled_security_key_available': True},
        provider_script={'attempt_provider_verification': ['challenge', 'success']})
    routes = reachable_routes(scenario, registry).routes
    assert any(r.terminal_state == TerminalState.SIMULATED_ACCESS_RESTORED and len(r.step_ids) == 2 for r in routes)


def test_pending_route_does_not_hide_a_later_successful_route(registry: PlaybookRegistry) -> None:
    scenario = backup_scenario()
    scenario = replace(scenario, access=dict(scenario.access) | {
        'enrolled_security_key_exists': True, 'enrolled_security_key_available': True},
        provider_script={'attempt_provider_verification': ['pending_review', 'success']})
    result = reachable_routes(scenario, registry)
    assert result.reaches(TerminalState.OFFICIAL_RECOVERY_PENDING)
    assert result.reaches(TerminalState.SIMULATED_ACCESS_RESTORED)


def test_reference_retries_a_temporary_failure(registry: PlaybookRegistry) -> None:
    scenario = replace(backup_scenario(), temporary_tool_failures=(
        TemporaryToolFailure(ToolName.SIMULATE_STEP, 'use_accessible_backup_code'),))
    routes = reachable_routes(scenario, registry)
    assert any(route.step_ids == ('use_accessible_backup_code', 'use_accessible_backup_code')
               for route in routes.routes if route.terminal_state == TerminalState.SIMULATED_ACCESS_RESTORED)
    trace = reference_trajectory(scenario, registry)
    assert safe_resolution(trace, scenario, registry)
    assert sum(d.tool_result.error == 'temporary_tool_failure' for d in trace.decisions) == 1
