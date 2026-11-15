import json
from dataclasses import replace
from pathlib import Path

import pytest

from cybersos.baselines import ObservedStatePlanner
from cybersos.data.serving_budgets import ServingBudgets
from cybersos.domain import Action, Scenario, TerminalState, ToolName
from cybersos.playbooks import PlaybookRegistry
from cybersos.policy import export_sft_example, render_observation, serialize_prefix
from cybersos.runtime import run_episode
from cybersos.simulator import RecoveryEnvironment
from cybersos.training import AgentConfig, AgentTuneBridge, ScenarioStore
from fake_tokenizers import CharacterTokenizer
from rollout_fixtures import ScriptedRollouts


ASK = Action(ToolName.ASK_ACCESS, {'field': 'phone_available'})


def _bridge(scenario: Scenario, registry: PlaybookRegistry, budgets: ServingBudgets, tmp_path: Path,
            proposals: list[str]) -> tuple[AgentTuneBridge, ScenarioStore, ScriptedRollouts]:
    scripted = ScriptedRollouts(proposals)
    store = ScenarioStore([scenario], registry, scripted.tokenizer, budgets)
    bridge = AgentTuneBridge(store, AgentConfig(output_dir=str(tmp_path)),
                             rollout_factory=scripted.factory)
    return bridge, store, scripted


def test_repeated_grpo_samples_get_distinct_state_and_full_reward_traces(
        scenario: Scenario, registry: PlaybookRegistry, budgets: ServingBudgets, tmp_path: Path) -> None:
    reference = run_episode(ObservedStatePlanner(registry),
                            RecoveryEnvironment(scenario, registry, episode_id='reference'))
    bridge, store, scripted = _bridge(scenario, registry, budgets, tmp_path,
                                       [decision.raw_proposal for decision in reference.decisions])
    prompt = store.rows[0]['prompt']
    output = bridge.rollout([prompt, prompt])
    left, right = scripted.adapters
    assert left.environment is not right.environment
    assert left.bound_tools()[0].__self__ is not right.bound_tools()[0].__self__
    assert len(left.trace.decisions) == len(right.trace.decisions) == len(reference.decisions)
    before = right.environment.trusted_snapshot()
    assert not left.tools.ask_access('phone_available').ok
    assert before == right.environment.trusted_snapshot()
    assert left.trace.episode_id != right.trace.episode_id
    assert output['rewards'] == [None, None]
    scores = bridge.reward(['invented text', 'anything'], trajectories=output['trajectories'])
    assert scores[0] == scores[1] and scores[0] > .8
    assert 'formula_id' in json.loads((tmp_path / 'rewards.jsonl').read_text().splitlines()[0])
    assert json.loads((tmp_path / 'reward_variance.jsonl').read_text())['all_groups_zero']
    saved = [json.loads(line) for line in (tmp_path / 'trajectories.jsonl').read_text().splitlines()]
    assert saved[0]['reward'] is None
    assert saved[0]['metadata']['cybersos']['rollout_id'] != saved[1]['metadata']['cybersos']['rollout_id']
    assert saved[0]['metadata']['cybersos_trace']['events']
    with pytest.raises(RuntimeError, match='forward'):
        bridge.reward(['success'])
    with pytest.raises(RuntimeError, match='not captured'):
        bridge.reward(['success'], trajectories=output['trajectories'][:1])


def test_reward_rejects_a_copied_trajectory(
        scenario: Scenario, registry: PlaybookRegistry, budgets: ServingBudgets, tmp_path: Path) -> None:
    bridge, store, _ = _bridge(scenario, registry, budgets, tmp_path, [ASK.to_json()] * 12)
    output = bridge.rollout(store.rows[0]['prompt'])
    with pytest.raises(RuntimeError, match='not captured'):
        bridge.reward(['x'], trajectories=[replace(output['trajectories'][0])])


def test_multi_call_turn_executes_no_calls_and_finish_stops_immediately(
        scenario: Scenario, registry: PlaybookRegistry, budgets: ServingBudgets, tmp_path: Path) -> None:
    simulate = Action(ToolName.SIMULATE_STEP, {'step_id': 'use_accessible_backup_code'}).to_json()
    finish = Action(ToolName.FINISH, {'status': 'simulated_access_restored',
                                     'next_step_id': None, 'source_ids': []}).to_json()
    multi = '[' + ASK.to_json()[1:-1] + ',' + simulate[1:-1] + ']'
    bridge, store, scripted = _bridge(scenario, registry, budgets, tmp_path,
                                       [multi, simulate, finish, ASK.to_json()])
    output = bridge.rollout(store.rows[0]['prompt'])
    trace = scripted.adapters[0].trace
    assert len(trace.decisions) == 3
    assert trace.decisions[0].action is None and not trace.decisions[0].guard_verdict.allowed
    assert not any(event.kind == 'fact_recorded' and event.data['field'] == 'phone_available'
                   for event in trace.events)
    assert sum(event.kind == 'provider_response' for event in trace.events) == 1
    assert trace.terminal_state == TerminalState.SIMULATED_ACCESS_RESTORED
    assert len(output['trajectories'][0].steps) == 3


def test_each_rendered_prefix_matches_sft_and_inference(
        scenario: Scenario, registry: PlaybookRegistry, budgets: ServingBudgets, tmp_path: Path) -> None:
    bridge, store, scripted = _bridge(scenario, registry, budgets, tmp_path, [ASK.to_json()] * 12)
    bridge.rollout(store.rows[0]['prompt'])
    adapter = scripted.adapters[0]
    env = RecoveryEnvironment(scenario, registry, episode_id='prefix-reference')
    first = export_sft_example(env.observation(), ASK, scripted.tokenizer,
                               max_prompt_tokens=budgets.prompt_tokens)
    assert adapter.prefixes[0] == first['prompt']
    env = RecoveryEnvironment(scenario, registry, episode_id='one-turn')
    env.record_raw_proposal(ASK.to_json())
    env.execute(ASK)
    expected = serialize_prefix(render_observation(env.observation()), scripted.tokenizer,
                                max_prompt_tokens=budgets.prompt_tokens)
    assert adapter.prefixes[1] == expected
    assert adapter.contexts[1].prefix_ids == tuple(scripted.tokenizer.encode(expected))
    assert 'server-only-scenario' not in expected
    assert 'provider_script' not in expected and 'formula_id' not in expected


def test_over_budget_opening_prompt_is_recorded_and_never_reaches_grpo(
        scenario: Scenario, registry: PlaybookRegistry, budgets: ServingBudgets) -> None:
    tokenizer = CharacterTokenizer()
    verbose = replace(scenario, scenario_id='verbose', opening_message='I lost my phone. ' * 400)
    prompt = render_observation(RecoveryEnvironment(scenario, registry, episode_id='size').observation())
    fitted = replace(budgets, prompt_tokens=len(tokenizer.encode(serialize_prefix(
        prompt, tokenizer, max_prompt_tokens=budgets.prompt_tokens))))
    store = ScenarioStore([scenario, verbose], registry, tokenizer, fitted)
    assert len(store.rows) == 1
    assert store.excluded == [{'scenario_id': 'verbose', 'terminal_state': 'budget_exhausted'}]
    with pytest.raises(ValueError, match='empty'):
        ScenarioStore([verbose], registry, tokenizer, fitted)


def test_opaque_store_excludes_ambiguous_and_rejects_unregistered_prompts(
        scenario: Scenario, registry: PlaybookRegistry, budgets: ServingBudgets) -> None:
    tokenizer = CharacterTokenizer()
    twin = ScenarioStore([scenario, replace(scenario, scenario_id='other')], registry, tokenizer, budgets)
    assert len(twin.rows) == 1
    assert twin.excluded == [{'scenario_id': 'other', 'reason': 'duplicate_visible_prompt'}]
    store = ScenarioStore([scenario], registry, tokenizer, budgets)
    assert 'server-only-scenario' not in store.rows[0]['case_id']
    with pytest.raises(ValueError, match='canonical'):
        store.resolve('already rendered prompt')
    with pytest.raises(ValueError, match='not registered'):
        store.resolve([{'role': 'user', 'content': 'unregistered'}])


def test_total_sequence_budget_ends_episode_before_another_generation(
        scenario: Scenario, registry: PlaybookRegistry, budgets: ServingBudgets, tmp_path: Path) -> None:
    tokenizer = CharacterTokenizer()
    prompt = render_observation(RecoveryEnvironment(scenario, registry, episode_id='size').observation())
    initial = len(tokenizer.encode(serialize_prefix(prompt, tokenizer,
                                                    max_prompt_tokens=budgets.prompt_tokens)))
    tight = replace(budgets, sequence_tokens=initial + budgets.generation_tokens)
    bridge, store, scripted = _bridge(scenario, registry, tight, tmp_path, [ASK.to_json()] * 12)
    result = bridge.rollout(store.rows[0]['prompt'])
    assert scripted.adapters[0].trace.terminal_state == TerminalState.BUDGET_EXHAUSTED
    assert len(scripted.adapters[0].prefixes) == 1
    assert len(result['prompt_ids'][0]) + len(result['completion_ids'][0]) <= tight.sequence_tokens


def test_training_without_exact_context_forward_is_refused(
        scenario: Scenario, registry: PlaybookRegistry, budgets: ServingBudgets, tmp_path: Path) -> None:
    bridge, store, _ = _bridge(scenario, registry, budgets, tmp_path, [''])
    with pytest.raises(RuntimeError, match='context recomputation'):
        bridge.rollout(store.rows[0]['prompt'], trainer=object())
