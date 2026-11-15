import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from cybersos.data.scenario_loading import episode_from_mapping
from cybersos.data.scenario_records import Split
from cybersos.data.serving_budgets import ServingBudgets
from cybersos.domain import Scenario, TerminalState
from cybersos.playbooks import PlaybookRegistry
from cybersos.policy import ChatTokenizer, PromptBudgetExceeded, render_observation, serialize_prefix
from cybersos.serialization import read_jsonl
from cybersos.simulator import RecoveryEnvironment


def prompt_key(prompt: Any) -> str:
    """Route by the canonical conversation; malformed lists simply never match a registration."""
    messages = prompt['prompt'] if isinstance(prompt, dict) and 'prompt' in prompt else prompt
    if not isinstance(messages, list) or not messages:
        raise ValueError('GRPO prompts must be canonical unrendered conversations')
    return json.dumps(messages, sort_keys=True, separators=(',', ':'))


@dataclass(frozen=True)
class TrainingCase:
    case_id: str
    scenario: Scenario


def load_training_scenarios(path: str | Path) -> tuple[Scenario, ...]:
    episodes = tuple(episode_from_mapping(row) for row in read_jsonl(path))
    if not episodes or any(episode.split != Split.TRAIN for episode in episodes):
        raise ValueError('Only explicitly labeled training scenarios may enter agent optimization')
    return tuple(episode.scenario for episode in episodes)


def select_pilot_scenarios(scenarios: tuple[Scenario, ...], count: int, *,
                           seed: int) -> tuple[Scenario, ...]:
    """A seeded subset for the bounded agent pilot, kept in corpus order."""
    if count > len(scenarios):
        raise ValueError(f'Pilot needs {count} training scenarios; only {len(scenarios)} exist')
    chosen = set(random.Random(seed).sample(range(len(scenarios)), count))
    return tuple(scenario for index, scenario in enumerate(scenarios) if index in chosen)


class ScenarioStore:
    """Server-owned map from opaque prompts to hidden scenarios.

    An opening prompt over the serving prompt budget can never be generated from, so it is
    recorded as budget exhausted instead of reaching GRPO with an empty prompt. A scenario whose
    visible prompt is already registered is excluded, so every prompt routes to one hidden state.
    """

    def __init__(self, scenarios: Iterable[Scenario], registry: PlaybookRegistry,
                 tokenizer: ChatTokenizer, budgets: ServingBudgets, *, seed: int = 42) -> None:
        self.registry = registry
        self.budgets = budgets
        self._cases: dict[str, TrainingCase] = {}
        self._prompts: dict[str, str] = {}
        self.rows: list[dict[str, object]] = []
        self.excluded: list[dict[str, str]] = []
        for index, scenario in enumerate(scenarios):
            opaque = hashlib.sha256(f'cybersos-case-v1:{seed}:{index}'.encode()).hexdigest()[:24]
            env = RecoveryEnvironment(scenario, registry, episode_id='prompt-construction',
                                      action_budget=budgets.actions)
            messages = render_observation(env.observation())
            try:
                serialize_prefix(messages, tokenizer, max_prompt_tokens=budgets.prompt_tokens)
            except PromptBudgetExceeded:
                self.excluded.append({'scenario_id': scenario.scenario_id,
                                      'terminal_state': TerminalState.BUDGET_EXHAUSTED.value})
                continue
            key = prompt_key(messages)
            if key in self._prompts:
                # Rewards must come from the scenario that produced the prompt; a second hidden
                # state behind the same visible prompt would make that routing ambiguous.
                self.excluded.append({'scenario_id': scenario.scenario_id,
                                      'reason': 'duplicate_visible_prompt'})
                continue
            self._cases[opaque] = TrainingCase(opaque, scenario)
            self._prompts[key] = opaque
            self.rows.append({'prompt': messages, 'case_id': opaque})
        if not self.rows:
            raise ValueError('Training scenario store is empty')

    def resolve(self, prompt: Any) -> TrainingCase:
        key = prompt_key(prompt)
        if key not in self._prompts:
            raise ValueError('Prompt is not registered in the server-owned scenario store')
        case_id = self._prompts[key]
        if isinstance(prompt, dict) and prompt.get('case_id', case_id) != case_id:
            raise ValueError('Opaque case ID does not match the registered conversation')
        return self._cases[case_id]

    def fresh_environment(self, case: TrainingCase, rollout_id: str) -> RecoveryEnvironment:
        return RecoveryEnvironment(case.scenario, self.registry, episode_id=f'episode-{rollout_id}',
                                   action_budget=self.budgets.actions)
