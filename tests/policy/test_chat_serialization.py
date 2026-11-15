from collections.abc import Callable

import pytest
from fake_tokenizers import CharacterTokenizer

from cybersos.domain import AccessField, Action, ToolName
from cybersos.policy import (
    POLICY, PromptBudgetExceeded, action_completion, chat_template_sha256, export_sft_example,
    render_observation, serialize_prefix,
)
from cybersos.simulator import RecoveryEnvironment


@pytest.mark.parametrize('after_tool', [False, True])
def test_sft_and_inference_share_exact_first_and_post_tool_prefixes(
        policy_env: Callable[..., RecoveryEnvironment], after_tool: bool) -> None:
    env = policy_env(access={'backup_code_accessible_now': False})
    if after_tool:
        env.execute(Action(ToolName.ASK_ACCESS, {'field': 'backup_code_accessible_now'}))
    observation = env.observation()
    action = Action(ToolName.ASK_ACCESS, {'field': AccessField.SAFE_OTHER_DEVICE.value})
    tokenizer = CharacterTokenizer()
    messages = render_observation(observation)
    example = export_sft_example(observation, action, tokenizer, max_prompt_tokens=50000)
    assert len(tokenizer.conversations) == 1
    assert tokenizer.conversations[0] == messages
    assert example['prompt'].count('<chat>') == 1
    assert example['prompt'].endswith('<assistant>')
    assert example['prompt'].count(POLICY) == 1
    assert example['completion'] == action.to_json() + '<eot>'
    assert example['completion'].count('<eot>') == 1
    assert example['prompt'] == serialize_prefix(messages, CharacterTokenizer(), max_prompt_tokens=50000)
    if after_tool:
        assert 'ask_access result: backup_code_accessible_now=false' in example['prompt']
        assert 'backup_code_accessible_now = false [scripted_answer]' in example['prompt']


def test_rendered_sft_string_is_rejected_as_an_inference_prompt(
        policy_env: Callable[..., RecoveryEnvironment]) -> None:
    tokenizer = CharacterTokenizer()
    prefix = serialize_prefix(render_observation(policy_env().observation()), tokenizer,
                              max_prompt_tokens=50000)
    with pytest.raises(TypeError, match='never a rendered string'):
        serialize_prefix(prefix, tokenizer)  # type: ignore[arg-type]
    assert len(tokenizer.conversations) == 1


def test_overflow_rejects_without_silently_dropping_facts(
        policy_env: Callable[..., RecoveryEnvironment]) -> None:
    observation = policy_env(initial_facts={'backup_code_accessible_now': True}).observation()
    messages = render_observation(observation)
    tokenizer = CharacterTokenizer()
    with pytest.raises(PromptBudgetExceeded, match='no truncation'):
        serialize_prefix(messages, tokenizer, max_prompt_tokens=5)
    assert 'backup_code_accessible_now' in tokenizer.conversations[0][1]['content']
    action = Action(ToolName.ASK_ACCESS, {'field': 'safe_other_device'})
    with pytest.raises(PromptBudgetExceeded, match='no truncation'):
        action_completion(action, tokenizer, max_completion_tokens=1)


@pytest.mark.parametrize('text', [
    '[]', '[{"tool_name":"ask_access","parameters":{"field":"unknown"}}]',
    '[{"tool_name":"ask_access","parameters":{"field":"safe_other_device"}}]<eot>',
    '[{"tool_name":"finish","parameters":{"status":"simulated_access_restored"}}]',
])
def test_invalid_targets_are_not_exported_as_training_actions(text: str) -> None:
    with pytest.raises(ValueError):
        action_completion(text, CharacterTokenizer())


def test_frozen_template_hash_is_the_named_default_template_rendering_uses() -> None:
    # Tiny Aya's tokenizer config ships named templates, which transformers loads as a dict.
    plain, named = CharacterTokenizer(), CharacterTokenizer()
    named.chat_template = {'default': plain.chat_template, 'tool_use': 'another template'}
    assert chat_template_sha256(named) == chat_template_sha256(plain)
    named.chat_template = {'tool_use': 'another template'}
    with pytest.raises(ValueError):
        chat_template_sha256(named)
