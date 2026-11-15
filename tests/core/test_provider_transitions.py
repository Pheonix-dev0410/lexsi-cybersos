from collections.abc import Callable

import pytest

from cybersos.domain import AccessField, TerminalState
from cybersos.simulator import EpisodeTools, RecoveryEnvironment


def test_denied_reauthentication_changes_permitted_route(make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object]) -> None:
    facts = backup_facts | dict(active_session_elsewhere=True, reauthentication_available=True,
                               account_access_available=True)
    env = make_env(facts=facts, incident='exposed_password', script={'use_trusted_session': 'denial'})
    tools = EpisodeTools(env)
    assert tools.check_step('change_exposed_password').data['status'] == 'ready'
    assert tools.simulate_step('use_trusted_session').data['provider_response'] == 'denial'
    assert tools.check_step('change_exposed_password').data['status'] == 'blocked'
    assert tools.check_step('official_account_recovery').data['status'] == 'ready'
    assert not tools.simulate_step('use_trusted_session').ok


def test_official_recovery_is_pending_never_restored(make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object]) -> None:
    env = make_env(facts=backup_facts, script={'recovery_attempt': 'success'})
    tools = EpisodeTools(env)
    assert tools.simulate_step('official_account_recovery').data['provider_response'] == 'pending_review'
    assert not env.trusted_snapshot().verified_access_restored
    assert tools.finish(TerminalState.OFFICIAL_RECOVERY_PENDING, 'official_account_recovery', ('google_recover',)).ok
    assert env.task_outcome().value == 'objective_met'


@pytest.mark.parametrize('response', ['success', 'challenge', 'pending_review', 'denial'])
def test_provider_outcomes_are_events_not_guaranteed_success(make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object], response: str) -> None:
    env = make_env(facts=backup_facts, script={'use_accessible_backup_code': response})
    result = EpisodeTools(env).simulate_step('use_accessible_backup_code')
    assert result.ok
    assert result.data['provider_response'] == response
    assert env.trusted_snapshot().verified_access_restored == (response == 'success')
    assert len([e for e in env.trusted_snapshot().events if e.kind == 'provider_response']) == 1


def test_repetition_cannot_create_progress(make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object]) -> None:
    env = make_env(facts=backup_facts, script={'use_accessible_backup_code': ['success', 'success']})
    tools = EpisodeTools(env)
    assert tools.simulate_step('use_accessible_backup_code').ok
    for _ in range(30):
        assert not tools.simulate_step('use_accessible_backup_code').ok
    snapshot = env.trusted_snapshot()
    assert snapshot.completed_steps == frozenset({'use_accessible_backup_code'})
    assert len([e for e in snapshot.events if e.kind == 'provider_response']) == 1
    assert snapshot.action_count == 12
    assert snapshot.terminal_state == TerminalState.BUDGET_EXHAUSTED


def test_later_questions_observe_current_simulated_access(make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object]) -> None:
    env = make_env(facts=backup_facts, access={'account_access_available': False},
                   script={'use_accessible_backup_code': 'success'})
    tools = EpisodeTools(env)
    tools.simulate_step('use_accessible_backup_code')
    result = tools.ask_access(AccessField.ACCOUNT_ACCESS_AVAILABLE)
    assert result.data['value'] == 'true'
    assert env.trusted_snapshot().hidden_access['account_access_available'] == 'true'
