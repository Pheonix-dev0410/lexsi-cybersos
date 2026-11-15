from collections.abc import Callable

import pytest

from cybersos.domain import TerminalState
from cybersos.simulator import EpisodeTools, RecoveryEnvironment


def test_fabricated_finish_cannot_change_verified_state(make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object]) -> None:
    env = make_env(facts=backup_facts)
    result = EpisodeTools(env).finish(TerminalState.SIMULATED_ACCESS_RESTORED, None, ())
    assert not result.ok
    assert env.terminal_state == TerminalState.INVALID_FINISH
    assert not env.trusted_snapshot().verified_access_restored
    assert any(e.kind == 'finish_proposed' for e in env.trusted_snapshot().events)


def test_finish_after_success_and_all_tools_refuse_after_done(make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object]) -> None:
    env = make_env(facts=backup_facts, script={'use_accessible_backup_code': 'success'})
    tools = EpisodeTools(env)
    tools.simulate_step('use_accessible_backup_code')
    assert tools.finish(TerminalState.SIMULATED_ACCESS_RESTORED, None, ()).ok
    snapshot = env.trusted_snapshot()
    assert not tools.ask_access('phone_available').ok
    assert not tools.lookup_playbook('google_personal', 'lost_phone').ok
    assert not tools.check_step('use_accessible_backup_code').ok
    assert not tools.simulate_step('official_account_recovery').ok
    assert not tools.finish(TerminalState.SIMULATED_ACCESS_RESTORED, None, ()).ok
    assert snapshot == env.trusted_snapshot()
    with pytest.raises(ValueError):
        env.update_fact('phone_available', True)


@pytest.mark.parametrize(('field', 'step'), [('organization_managed', 'managed_account_boundary'),
                                           ('child_account', 'child_account_boundary')])
def test_boundary_rules_require_actual_handoff(make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object], field: str, step: str) -> None:
    env = make_env(facts=backup_facts | {field: True})
    tools = EpisodeTools(env)
    assert tools.check_step('official_account_recovery').data['status'] == 'blocked'
    assert tools.simulate_step(step).ok
    assert tools.finish(TerminalState.NEEDS_PROVIDER_OR_ADMIN, step, ('google_recover',)).ok
    assert not env.trusted_snapshot().verified_access_restored


def test_protection_requires_all_scenario_steps(make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object]) -> None:
    required = ('change_exposed_password', 'review_security_activity')
    facts = backup_facts | dict(account_access_available=True, reauthentication_available=True)
    env = make_env(facts=facts, incident='exposed_password', required=required,
                   script={'protective_step': ['success', 'success']})
    tools = EpisodeTools(env)
    tools.simulate_step(required[0])
    assert TerminalState.PROTECTIVE_WORKFLOW_COMPLETED not in env.guard_context().supported_terminals
    tools.simulate_step(required[1])
    assert tools.finish(TerminalState.PROTECTIVE_WORKFLOW_COMPLETED, None, ()).ok
