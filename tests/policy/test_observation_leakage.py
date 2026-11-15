import json
from dataclasses import replace
from typing import Callable

import pytest

from cybersos.domain import AccessField, Action, ToolName
from cybersos.policy import render_observation
from cybersos.simulator import RecoveryEnvironment, ToolResult


@pytest.mark.parametrize('access', [
    {'backup_code_exists': True, 'backup_code_accessible_now': False,
     'backup_code_storage': 'same_locked_account'},
    {'independent_passkey_exists': True, 'independent_passkey_available': False},
    {'enrolled_security_key_exists': True, 'enrolled_security_key_available': False},
    {'alternate_number_exists': True, 'alternate_number_on_lost_phone': True,
     'alternate_number_accessible': False},
    {'recovery_email_exists': True, 'recovery_email_accessible': False},
    {'organization_managed': True}, {'child_account': True},
    {'device_powered': False, 'device_online': False, 'find_hub_enabled': True},
])
def test_diagnostic_hidden_state_cannot_change_visible_prefix(
        policy_env: Callable[..., RecoveryEnvironment], access: dict[str, object]) -> None:
    first = policy_env(access=access)
    second = policy_env(access={}, provider_script={}, scenario_id='another_test_split',
                        objective='needs_provider_or_admin', account_owner=False)
    assert render_observation(first.observation()) == render_observation(second.observation())
    text = json.dumps(render_observation(first.observation()))
    assert 'HIDDEN_' not in text
    assert 'provider_script' not in text
    assert 'hidden_access' not in text


@pytest.mark.parametrize('field', list(AccessField))
def test_every_access_field_stays_hidden_until_observed(
        policy_env: Callable[..., RecoveryEnvironment], field: AccessField) -> None:
    value = 'independent' if field == AccessField.BACKUP_CODE_STORAGE else True
    hidden = policy_env(access={field.value: value})
    empty = policy_env()
    assert render_observation(hidden.observation()) == render_observation(empty.observation())


def test_facts_preserve_provenance_conflicts_and_corrections(
        policy_env: Callable[..., RecoveryEnvironment]) -> None:
    env = policy_env(initial_facts={'backup_code_accessible_now': True})
    env.update_fact(AccessField.BACKUP_CODE_ACCESSIBLE_NOW, False)
    conflicted = env.observation()
    text = render_observation(conflicted)[1]['content']
    assert ('backup_code_accessible_now = unknown [user_reported; conflicting reports; reported false; '
            'earlier true from intake]') in text
    env.update_fact(AccessField.BACKUP_CODE_ACCESSIBLE_NOW, True, correction=True)
    text = render_observation(env.observation())[1]['content']
    assert ('backup_code_accessible_now = true [user_reported; correction; earlier true from intake; '
            'earlier false from user_reported]') in text


def test_rule_context_is_retrieved_and_never_filtered_by_hidden_access(
        policy_env: Callable[..., RecoveryEnvironment]) -> None:
    first = policy_env(access={'backup_code_accessible_now': True})
    second = policy_env(access={'backup_code_accessible_now': False})
    lookup = Action(ToolName.LOOKUP_PLAYBOOK,
                    {'provider': 'google_personal', 'incident': 'lost_phone'})
    assert 'google_backup_code' not in render_observation(first.observation())[1]['content']
    first.execute(lookup)
    second.execute(lookup)
    messages = render_observation(first.observation())
    assert messages == render_observation(second.observation())
    text = messages[1]['content']
    assert 'use_accessible_backup_code: ' in text and 'backup_code_accessible_now=true' in text
    assert '[google_2sv]' in text
    assert 'lookup_playbook result: retrieved_rules=' in text
    assert 'simulation_effect' not in text
    assert '"real_account_effect"' not in text


def test_closed_history_projection_drops_hidden_metadata_at_each_level(
        policy_env: Callable[..., RecoveryEnvironment]) -> None:
    result = ToolResult(ToolName.LOOKUP_PLAYBOOK, True, {
        'gold_actions': ['GOLD_SENTINEL'], 'hidden_state': {'access': 'HIDDEN_SENTINEL'},
        'rules': [{'step_id': 'public_step', 'instruction': 'Public guidance',
                   'requires': {'account_owner': 'true'}, 'source_ids': [],
                   'gold': 'GOLD_SENTINEL', 'split': 'SPLIT_SENTINEL',
                   'provider_script': 'SCRIPT_SENTINEL'}]})
    observation = replace(policy_env().observation(), history=(result,))
    text = json.dumps(render_observation(observation))
    assert 'public_step' in text
    assert 'SENTINEL' not in text
    bad = ToolResult(ToolName.CHECK_STEP, True, {'step_id': {'gold': 'GOLD_SENTINEL'}})
    with pytest.raises(ValueError, match='observed text'):
        render_observation(replace(observation, history=(bad,)))
    with pytest.raises(ValueError, match='envelope scalars'):
        bad = ToolResult(ToolName.CHECK_STEP, False, {}, error={'gold': 'GOLD_SENTINEL'})
        render_observation(replace(observation, history=(bad,)))


def test_scenario_and_trusted_snapshot_are_not_renderable(
        policy_env: Callable[..., RecoveryEnvironment]) -> None:
    env = policy_env()
    with pytest.raises(TypeError, match='core Observation'):
        render_observation(env.trusted_snapshot())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match='core Observation'):
        render_observation({'hidden_state': 'secret'})  # type: ignore[arg-type]
    with pytest.raises(ValueError, match='structured'):
        render_observation(replace(env.observation(), observation_mode='raw'))
