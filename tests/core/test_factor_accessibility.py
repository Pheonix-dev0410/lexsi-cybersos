from collections.abc import Callable

from cybersos.domain import AccessField
from cybersos.simulator import EpisodeTools, RecoveryEnvironment


def test_lost_phone_is_not_a_factor(make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object]) -> None:
    env = make_env(facts=backup_facts | {'phone_available': False, 'device_signed_in': True})
    assert EpisodeTools(env).check_step('use_available_phone').data['status'] == 'blocked'


def test_number_in_lost_phone_is_unavailable(make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object]) -> None:
    facts = backup_facts | dict(phone_available=False, alternate_number_accessible=True,
                               alternate_number_on_lost_phone=True)
    assert EpisodeTools(make_env(facts=facts)).check_step('use_alternate_number').data['status'] == 'blocked'


def test_circular_backup_storage_is_unavailable(make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object]) -> None:
    env = make_env(facts=backup_facts | {'backup_code_storage': 'same_locked_account'})
    assert EpisodeTools(env).check_step('use_accessible_backup_code').data['status'] == 'blocked'
    hidden = make_env(access={'backup_code_exists': True, 'backup_code_accessible_now': True,
                              'backup_code_storage': 'same_locked_account'})
    assert EpisodeTools(hidden).ask_access(AccessField.BACKUP_CODE_ACCESSIBLE_NOW).data['value'] == 'false'
    assert len(hidden.observation().facts) == 1


def test_unknown_prerequisites_do_not_consult_hidden_facts(make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object]) -> None:
    env = make_env(access=backup_facts)
    result = EpisodeTools(env).check_step('use_accessible_backup_code')
    assert result.data['status'] == 'needs_information'
    assert not env.observation().facts
    assert not EpisodeTools(env).simulate_step('use_accessible_backup_code').ok


def test_semantic_questions_are_independent_of_turn_number(make_env: Callable[..., RecoveryEnvironment]) -> None:
    access = dict(phone_available=False, recovery_email_accessible=True)
    first, second = make_env(access=access), make_env(access=access)
    a, b = EpisodeTools(first), EpisodeTools(second)
    assert a.ask_access(AccessField.RECOVERY_EMAIL_ACCESSIBLE).data['value'] == 'true'
    assert a.ask_access(AccessField.PHONE_AVAILABLE).data['value'] == 'false'
    assert b.ask_access(AccessField.PHONE_AVAILABLE).data['value'] == 'false'
    assert b.ask_access(AccessField.RECOVERY_EMAIL_ACCESSIBLE).data['value'] == 'true'
