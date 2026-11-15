from collections.abc import Callable

from cybersos.domain import Scenario, TerminalState
from cybersos.playbooks import PlaybookRegistry
from cybersos.simulator import EpisodeTools, RecoveryEnvironment


def test_same_scenario_has_fresh_facts_and_provider_cursor(registry: PlaybookRegistry, backup_facts: dict[str, object]) -> None:
    scenario = Scenario.from_mapping(dict(
        scenario_id='same', provider='google_personal', incident='lost_phone', account_owner=True,
        access={}, initial_facts=backup_facts, provider_script={'attempt_provider_verification': ['success']}))
    first = RecoveryEnvironment(scenario, registry, episode_id='one')
    second = RecoveryEnvironment(scenario, registry, episode_id='two')
    tools = EpisodeTools(first)
    tools.simulate_step('use_accessible_backup_code')
    tools.finish(TerminalState.SIMULATED_ACCESS_RESTORED, None, ())
    assert not second.done
    assert not second.trusted_snapshot().completed_steps
    assert EpisodeTools(second).simulate_step('use_accessible_backup_code').data['provider_response'] == 'success'


def test_episode_order_does_not_change_results(make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object]) -> None:
    def run(order: tuple[str, ...]) -> dict[str, object]:
        results = {}
        for response in order:
            env = make_env(facts=backup_facts, script={'use_accessible_backup_code': response})
            EpisodeTools(env).simulate_step('use_accessible_backup_code')
            results[response] = env.trusted_snapshot()
        return results
    assert run(('success', 'denial')) == run(('denial', 'success'))
