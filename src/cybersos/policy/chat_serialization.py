import hashlib
from typing import Protocol, Sequence

from cybersos.domain import Action
from cybersos.policy.observation_rendering import ChatMessage, render_observation
from cybersos.runtime.policy_errors import PolicyBudgetExceeded
from cybersos.safety import parse_action
from cybersos.safety.action_schema import schema_error
from cybersos.simulator import Observation


class ChatTokenizer(Protocol):
    eos_token: str | None
    chat_template: str | dict[str, str]

    def apply_chat_template(self, conversation: list[ChatMessage], *, tokenize: bool,
                            add_generation_prompt: bool) -> str: ...

    def encode(self, text: str, *, add_special_tokens: bool) -> list[int]: ...


class PromptBudgetExceeded(PolicyBudgetExceeded):
    pass


def chat_template_sha256(tokenizer: ChatTokenizer) -> str:
    """Hash of the template `apply_chat_template` renders with when no template name is given."""
    template = tokenizer.chat_template
    # Hub configs with named templates load as a dict; the unnamed call renders the 'default' one.
    if isinstance(template, dict):
        template = template.get('default')
    if not isinstance(template, str) or not template:
        raise ValueError('Tokenizer has no default chat template')
    return hashlib.sha256(template.encode()).hexdigest()


def serialize_prefix(messages: Sequence[ChatMessage], tokenizer: ChatTokenizer, *,
                     max_prompt_tokens: int = 1792) -> str:
    """Apply the tokenizer template once, ending at its assistant-generation boundary."""
    if isinstance(messages, (str, bytes)) or not messages:
        raise TypeError('Expected canonical role/content messages, never a rendered string')
    if max_prompt_tokens < 1:
        raise ValueError('Prompt budget must be positive')
    for message in messages:
        if (set(message) != {'role', 'content'} or message['role'] not in
                {'system', 'user', 'assistant'} or not isinstance(message['content'], str)):
            raise ValueError('Expected plain role/content messages without native tool fields')
    if messages[-1]['role'] != 'user':
        raise ValueError('A decision prefix must end with a user observation')
    prefix = tokenizer.apply_chat_template(list(messages), tokenize=False, add_generation_prompt=True)
    if not isinstance(prefix, str) or not prefix:
        raise ValueError('Tokenizer did not render a generation prefix')
    size = len(tokenizer.encode(prefix, add_special_tokens=False))
    if size > max_prompt_tokens:
        raise PromptBudgetExceeded(f'Prompt has {size} tokens; budget is {max_prompt_tokens}; no truncation')
    return prefix


def action_completion(action: Action | str, tokenizer: ChatTokenizer, *,
                      end_of_turn_token: str | None = None,
                      max_completion_tokens: int = 128) -> str:
    if isinstance(action, str):
        parsed = parse_action(action)
        if parsed.action is None:
            raise ValueError(parsed.error)
        action = parsed.action
    if not isinstance(action, Action) or (error := schema_error(action)):
        raise ValueError(error if isinstance(action, Action) else 'Expected an Action')
    token = end_of_turn_token or tokenizer.eos_token
    if not token or len(tokenizer.encode(token, add_special_tokens=False)) != 1:
        raise ValueError('An explicit single end-of-turn token is required')
    text = action.to_json()
    if token in text:
        raise ValueError('Action content contains an end-of-turn token')
    completion = text + token
    if len(tokenizer.encode(completion, add_special_tokens=False)) > max_completion_tokens:
        raise PromptBudgetExceeded('Completion exceeds generation budget; no truncation')
    return completion


def export_sft_example(observation: Observation, action: Action | str, tokenizer: ChatTokenizer, *,
                       max_prompt_tokens: int = 1792, max_completion_tokens: int = 128,
                       end_of_turn_token: str | None = None) -> dict[str, str]:
    """Export raw prompt/completion columns; downstream SFT must not template them again."""
    return {
        'prompt': serialize_prefix(render_observation(observation), tokenizer,
                                   max_prompt_tokens=max_prompt_tokens),
        'completion': action_completion(action, tokenizer, end_of_turn_token=end_of_turn_token,
                                        max_completion_tokens=max_completion_tokens),
    }
