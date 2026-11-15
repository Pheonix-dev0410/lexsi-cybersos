from types import SimpleNamespace
from typing import Any, Callable

from cybersos.data.serving_budgets import ServingBudgets
from cybersos.domain import Action, Scenario, ToolName
from cybersos.playbooks import PlaybookRegistry
from cybersos.simulator import RecoveryEnvironment
from cybersos.training.rollout_adapter import RolloutAdapter
from cybersos.training.rollout_patch import check_rollout_patch
from fake_tokenizers import CharacterTokenizer
from pinned_rollout_execution import load_cpu_rollout_control


def test_recorded_patch_applies_cleanly_to_pinned_copy() -> None:
    assert len(check_rollout_patch()) == 64


def test_patched_control_rejects_multicall_before_any_tool_execution(
        scenario: Scenario, registry: PlaybookRegistry, budgets: ServingBudgets) -> None:
    ask = Action(ToolName.ASK_ACCESS, {'field': 'phone_available'}).to_json()
    simulate = Action(ToolName.SIMULATE_STEP, {'step_id': 'use_accessible_backup_code'}).to_json()
    finish = Action(ToolName.FINISH, {'status': 'simulated_access_restored',
                                     'next_step_id': None, 'source_ids': []}).to_json()
    proposals = iter(['[' + ask[1:-1] + ',' + simulate[1:-1] + ']', simulate, finish])

    class ScriptedAdapter(RolloutAdapter):
        def run(self, generate: Callable[..., Any], extract: Callable[..., Any], tokenizer: Any,
                step_type: type, trajectory_type: type, completion_ids: list[int],
                logprobs: list[Any], tool_mask: list[int]) -> Any:
            def generate_scripted(messages: Any, schemas: Any) -> tuple[Any, ...]:
                raw = next(proposals)
                ids = tokenizer.encode(raw)
                completion_ids.extend(ids)
                logprobs.extend([(-.1, token) for token in ids])
                tool_mask.extend([1] * len(ids))
                return raw, {'role': 'assistant', 'content': raw}, [], {}

            return super().run(generate_scripted, extract, tokenizer, step_type, trajectory_type,
                                completion_ids, logprobs, tool_mask)

    env = RecoveryEnvironment(scenario, registry, episode_id='real-patched-control')
    adapter = ScriptedAdapter(env, budgets)
    execute = load_cpu_rollout_control()
    trajectory = execute(
        prompt=[], tools=adapter.bound_tools(), tools_enabled=True, engine=None, max_steps=12,
        pre_step_hook=None, post_step_hook=None, gen_kwargs={'_cybersos_adapter': adapter},
        trainer=SimpleNamespace(processing_class=CharacterTokenizer(), use_vllm=False))
    assert len(trajectory.steps) == 3
    assert isinstance(trajectory.task, str)
    assert not trajectory.metadata['cybersos_trace']['decisions'][0]['guard_verdict']['allowed']
    assert len([event for event in env.trusted_snapshot().events if event.kind == 'provider_response']) == 1
    assert not any(fact.field == 'phone_available' for fact in env.observation().facts)
