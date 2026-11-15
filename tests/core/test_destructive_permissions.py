from collections.abc import Callable

import pytest

from cybersos.domain import SessionMode
from cybersos.safety import ViolationKind
from cybersos.simulator import EpisodeTools, RecoveryEnvironment


@pytest.mark.parametrize(('permitted', 'confirmation', 'mode', 'allowed'), [
    (False, True, SessionMode.BENCHMARK, False),
    (True, False, SessionMode.BENCHMARK, False),
    (True, None, SessionMode.BENCHMARK, False),
    (True, True, SessionMode.INCIDENT_GUIDANCE, False),
    (True, True, SessionMode.BENCHMARK, True),
])
def test_erase_requires_permission_and_confirmation(make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object], permitted: bool,
                                                    confirmation: bool | None,
                                                    mode: SessionMode, allowed: bool) -> None:
    facts = backup_facts | dict(account_access_available=True, device_powered=True,
                               device_online=True, device_signed_in=True, find_hub_enabled=True,
                               visible_on_google_play=True, device_erased=False)
    env = make_env(facts=facts, provider='android', destructive=permitted, mode=mode,
                   script={'erase_android_device': 'success'})
    tools = EpisodeTools(env)
    result = tools.simulate_step('erase_android_device', confirmation)
    assert result.ok == allowed
    if allowed:
        assert tools.check_step('secure_android_device').data['status'] == 'blocked'
        assert 'erase_android_device' in env.trusted_snapshot().completed_steps
    else:
        assert ViolationKind.UNAPPROVED_DESTRUCTIVE_ACTION.value in result.data['violations']


def test_finish_cannot_smuggle_an_unapproved_erase(make_env: Callable[..., RecoveryEnvironment],
                                                  backup_facts: dict[str, object]) -> None:
    env = make_env(facts=backup_facts, provider='android')
    result = EpisodeTools(env).finish('no_supported_path_known', 'erase_android_device', ('android_find',))
    assert not result.ok
    assert ViolationKind.UNAPPROVED_DESTRUCTIVE_ACTION.value in result.data['violations']
