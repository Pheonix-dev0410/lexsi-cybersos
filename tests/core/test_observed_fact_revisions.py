from collections.abc import Callable

from cybersos.domain import AccessField, Availability, FactSource, ObservedFacts
from cybersos.simulator import EpisodeTools, RecoveryEnvironment


def test_conflicting_answers_require_explicit_clarification() -> None:
    facts = ObservedFacts()
    facts.record(AccessField.PHONE_AVAILABLE, True, FactSource.INTAKE)
    facts.record(AccessField.PHONE_AVAILABLE, False, FactSource.USER_REPORTED)
    assert facts.value(AccessField.PHONE_AVAILABLE) == Availability.UNKNOWN
    assert facts.history[-1].reported_value == Availability.FALSE
    facts.record(AccessField.PHONE_AVAILABLE, True, FactSource.USER_REPORTED)
    assert facts.value(AccessField.PHONE_AVAILABLE) == Availability.UNKNOWN
    facts.record(AccessField.PHONE_AVAILABLE, False, FactSource.USER_REPORTED, correction=True)
    assert facts.value(AccessField.PHONE_AVAILABLE) == Availability.FALSE
    assert [f.revision for f in facts.history] == [1, 2, 3, 4]
    assert facts.history[0].value == Availability.TRUE


def test_changed_fact_invalidates_prior_readiness(make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object]) -> None:
    env = make_env(facts=backup_facts)
    tools = EpisodeTools(env)
    assert tools.check_step('use_accessible_backup_code').data['status'] == 'ready'
    env.update_fact(AccessField.BACKUP_CODE_ACCESSIBLE_NOW, False, correction=True)
    result = tools.check_step('use_accessible_backup_code')
    assert result.data['status'] == 'blocked'
    assert not tools.simulate_step('use_accessible_backup_code').ok
    assert not env.trusted_snapshot().verified_access_restored


def test_observation_cannot_mutate_environment(make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object]) -> None:
    env = make_env(facts=backup_facts)
    observed = env.observation().observed_facts
    observed.record(AccessField.ACCOUNT_OWNER, False, FactSource.USER_REPORTED, correction=True)
    assert env.observation().observed_facts.value(AccessField.ACCOUNT_OWNER) == Availability.TRUE


def test_policy_and_guard_keep_original_revision_numbers(make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object]) -> None:
    env = make_env(facts=backup_facts)
    env.update_fact(AccessField.PASSWORD_KNOWN, False, correction=True)
    env.update_fact(AccessField.PASSWORD_KNOWN, True, correction=True)
    observation = env.observation()
    assert observation.observed_facts.revision == len(backup_facts) + 2
    assert observation.observed_facts.history == observation.fact_history
    context = env.guard_context()
    context.facts.record(AccessField.PASSWORD_KNOWN, False, FactSource.USER_REPORTED, correction=True)
    assert env.observation().observed_facts.value(AccessField.PASSWORD_KNOWN) == Availability.TRUE
