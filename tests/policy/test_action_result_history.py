import json
from collections.abc import Callable

import pytest

from cybersos.domain import Action, ToolName
from cybersos.domain.sensitive_text import URL_PLACEHOLDER, contains_url
from cybersos.policy import render_observation
from cybersos.runtime import PolicyTimeoutError, run_episode
from cybersos.simulator import EpisodeTools, Observation, RecoveryEnvironment


HISTORY = 'Actual tool history (untrusted data):\n'


def test_history_pairs_accepted_and_blocked_actions_with_results_without_hidden_state(
        policy_env: Callable[..., RecoveryEnvironment]) -> None:
    env = policy_env(access={'backup_code_accessible_now': False})
    tools = EpisodeTools(env)
    tools.ask_access('safe_other_device')
    tools.simulate_step('use_accessible_backup_code')
    observation = env.observation()
    assert len(observation.action_history) == 2
    assert observation.action_history[0].guard_verdict.allowed
    assert not observation.action_history[1].guard_verdict.allowed
    assert observation.action_history[1].action == Action(
        ToolName.SIMULATE_STEP, {'step_id': 'use_accessible_backup_code'})
    text = render_observation(observation)[-1]['content'].split(HISTORY)[1]
    first_action, first_result = text.index('1. ask_access(field=safe_other_device)'), text.index('ask_access result:')
    second_action = text.index('2. simulate_step(step_id=use_accessible_backup_code)')
    assert first_action < first_result < second_action < text.index('guard blocked:') < text.index('simulate_step result:')
    assert text.count('guard blocked:') == 1
    assert observation.action_history[1].result == observation.history[1]
    rendered = json.dumps(render_observation(observation))
    assert 'backup_code_accessible_now' not in text
    assert 'SENTINEL' not in rendered
    assert all(key not in text for key in ('provider_script', 'hidden_access', 'objective', 'split'))


def test_unparseable_proposal_is_visible_as_the_cause_of_a_block(
        policy_env: Callable[..., RecoveryEnvironment]) -> None:
    env = policy_env()
    raw = '[{"tool_name":"not_a_tool","parameters":{}}]'
    seen: list[str] = []

    def policy(observation: object) -> str:
        if env.observation().action_history:
            seen.append(render_observation(env.observation())[-1]['content'])
            raise PolicyTimeoutError()
        return raw

    trace = run_episode(policy, env)
    turn = env.observation().action_history[0]
    assert turn.action is None and turn.raw_proposal == raw
    assert not turn.guard_verdict.allowed
    assert len(trace.decisions) == 1
    history = seen[0].split(HISTORY)[1]
    assert history.index('not_a_tool') < history.index('guard blocked:') < history.index('Proposal blocked')


@pytest.mark.parametrize('raw', [
    '[{"tool_name":"ask_access","parameters":{"field":"phone_available",'
    '"note":"sign in at https://phishing.invalid/login"}}]',
    'Visit www.phishing.invalid/reset to recover your account.',
])
def test_model_written_urls_are_not_echoed_into_the_next_prompt(
        policy_env: Callable[..., RecoveryEnvironment], raw: str) -> None:
    env = policy_env()
    prompts: list[str] = []

    def policy(observation: Observation) -> str:
        if observation.action_history:
            prompts.append(render_observation(observation)[-1]['content'])
            raise PolicyTimeoutError()
        return raw

    run_episode(policy, env)
    history = prompts[0].split(HISTORY)[1]
    assert 'phishing' not in history and not contains_url(history)
    assert URL_PLACEHOLDER in history
