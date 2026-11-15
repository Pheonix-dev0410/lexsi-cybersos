from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from cybersos.data.decision_rows import decision_row, row_hash
from cybersos.data.decision_examples import DecisionExamples
from cybersos.data.decision_gates import (
    DecisionGates, check_counterfactual_preservation, check_export_count,
)
from cybersos.data.scenario_loading import load_training_episodes
from cybersos.data.split_artifacts import episode_mapping
from cybersos.data.scenario_records import Split
from cybersos.domain import Action, ToolName
from cybersos.playbooks import PlaybookRegistry
from cybersos.serialization import write_jsonl


def test_every_exported_target_matches_actual_turn(examples: DecisionExamples,
                                                   registry: PlaybookRegistry) -> None:
    gates = DecisionGates(list(examples.trajectories), registry)
    for row in examples.rows:
        assert gates.check(row, examples.provenance[row_hash(row)]) == ()
    replay = gates.replay(examples.trajectories[0]['trajectory_id'])
    assert not replay.observations[0].history
    assert replay.observations[1].history
    assert decision_row(replay.observations[1], replay.trace.decisions[1].raw_proposal) == examples.rows[1]
    first_tool = replay.trace.decisions[0].action.tool_name.value
    assert f'1. {first_tool}(' in examples.rows[1]['instruction']
    assert f'1. {first_tool}(' not in examples.rows[0]['instruction']


@pytest.mark.parametrize('defect,reason', [
    ('empty', 'empty_completion'), ('multiple', 'invalid_action'),
    ('infeasible', 'infeasible_action'), ('source', 'source_scope'),
    ('scope', 'rule_scope'), ('missing_context', 'missing_source_evidence'),
    ('root', 'root_provenance_mismatch'), ('hidden', 'observation_or_action_mismatch'),
])
def test_gate_rejects_defects(examples: DecisionExamples, registry: PlaybookRegistry,
                             defect: str, reason: str) -> None:
    row = dict(examples.rows[0])
    origins = deepcopy(examples.provenance[row_hash(row)])
    if defect == 'empty':
        row['output'] = ''
    elif defect == 'multiple':
        row['output'] = '[{}, {}]'
    elif defect == 'infeasible':
        row['output'] = Action(ToolName.SIMULATE_STEP, {'step_id': 'use_accessible_backup_code'}).to_json()
    elif defect == 'source':
        origins[0]['evidence']['sources']['unknown_source'] = {}
    elif defect == 'scope':
        row['output'] = Action(ToolName.SIMULATE_STEP, {'step_id': 'secure_android_device'}).to_json()
    elif defect == 'missing_context':
        origins[0]['evidence']['source_context'] = ''
    elif defect == 'root':
        origins[0]['split'] = 'test'
    elif defect == 'hidden':
        row['instruction'] = row['instruction'].replace('Observed facts', 'GOLD ROOT label. Observed facts')
    assert reason in DecisionGates(list(examples.trajectories), registry).check(row, origins)


def test_labeled_outcome_and_provider_results_are_replayed(examples: DecisionExamples,
                                                          registry: PlaybookRegistry) -> None:
    trajectories = deepcopy(examples.trajectories)
    trajectories[0]['terminal_state'] = 'simulated_access_restored'
    row = examples.rows[0]
    errors = DecisionGates(list(trajectories), registry).check(row, examples.provenance[row_hash(row)])
    assert any(error.startswith('replay_mismatch') for error in errors)
    trajectories = deepcopy(examples.trajectories)
    trajectories[0]['trace_signature'] = 'fabricated'
    errors = DecisionGates(list(trajectories), registry).check(row, examples.provenance[row_hash(row)])
    assert any(error.startswith('replay_mismatch') for error in errors)


def test_pair_loss_and_export_count_fail_closed(examples: DecisionExamples) -> None:
    reduced = deepcopy(examples.provenance)
    digest = next(iter(reduced))
    del reduced[digest]
    with pytest.raises(ValueError, match='collapsed_counterfactual_pair'):
        check_counterfactual_preservation(examples.provenance, reduced)
    with pytest.raises(ValueError, match='accepted_export_count_mismatch'):
        check_export_count(2, [examples.rows[0]])


def test_corpus_gate_catches_root_leakage(tmp_path: Path, training_episodes: tuple) -> None:
    train = training_episodes[0]
    leaked = replace(train, split=Split.DEV, scenario=replace(train.scenario, scenario_id='dev-paraphrase'))
    write_jsonl(tmp_path / 'train.jsonl', [episode_mapping(train)])
    write_jsonl(tmp_path / 'dev.jsonl', [episode_mapping(leaked)])
    write_jsonl(tmp_path / 'test.jsonl', [])
    with pytest.raises(ValueError, match='leakage'):
        load_training_episodes(tmp_path, 'full')


def test_unregistered_training_root_is_rejected(examples: DecisionExamples,
                                               registry: PlaybookRegistry) -> None:
    row = examples.rows[0]
    errors = DecisionGates(list(examples.trajectories), registry, training_episodes=[]).check(
        row, examples.provenance[row_hash(row)])
    assert 'nontraining_or_changed_scenario' in errors
