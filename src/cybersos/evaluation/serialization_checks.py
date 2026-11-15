import json
from typing import Any

from cybersos.baselines import GuidedQuestionnaire
from cybersos.data.diagnostic_scenarios import load_diagnostic_scenarios
from cybersos.playbooks import load_project_registry
from cybersos.policy import ServingContract, export_sft_example, render_observation, serialize_prefix
from cybersos.project_paths import DIAGNOSTIC_CASES_PATH
from cybersos.simulator import RecoveryEnvironment


class _StructuralTokenizer:
    eos_token = '<end>'
    chat_template = 'structural probe only; not the Tiny Aya tokenizer'

    def apply_chat_template(self, conversation: list[dict[str, str]], *, tokenize: bool,
                            add_generation_prompt: bool) -> str:
        return json.dumps(conversation, sort_keys=True) + ('assistant:' if add_generation_prompt else '')

    def encode(self, text: str, *, add_special_tokens: bool) -> list[int]:
        return [1] if text == self.eos_token else list(text.encode())


def check_serialization(contract: ServingContract, tokenizer: Any = None) -> dict[str, object]:
    actual = tokenizer is not None
    tokenizer = tokenizer if actual else _StructuralTokenizer()
    registry = load_project_registry()
    scenario = load_diagnostic_scenarios(DIAGNOSTIC_CASES_PATH)[0].scenario
    observation = RecoveryEnvironment(scenario, registry, episode_id='doctor').observation()
    action = GuidedQuestionnaire(registry)(observation)
    budget = contract.fields['budgets']['prompt_tokens'] if actual else 1_000_000
    end_token = contract.fields['serialization']['end_of_turn_token'] if actual else tokenizer.eos_token
    exported = export_sft_example(observation, action, tokenizer, max_prompt_tokens=budget,
                                  max_completion_tokens=contract.fields['budgets']['generation_tokens']
                                  if actual else 1_000_000, end_of_turn_token=end_token)
    inference = serialize_prefix(render_observation(observation), tokenizer, max_prompt_tokens=budget)
    if exported['prompt'] != inference or not exported['completion'].endswith(end_token):
        raise ValueError('SFT and inference serialization disagree')
    if exported['completion'].count(end_token) != 1:
        raise ValueError('Completion must contain exactly one end-of-turn token')
    return {'status': 'passed', 'scope': 'real pinned tokenizer' if actual else 'offline structural probe',
            'same_prefix_tokens': tokenizer.encode(exported['prompt'], add_special_tokens=False) ==
            tokenizer.encode(inference, add_special_tokens=False),
            'real_tokenizer_check': 'passed' if actual else 'not run; requires Tiny Aya tokenizer access',
            'single_completion_end_token': True}
