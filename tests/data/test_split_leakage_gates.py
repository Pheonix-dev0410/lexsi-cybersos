from dataclasses import replace

import pytest

from cybersos.data.scenario_fingerprints import root_hash
from cybersos.data.scenario_records import FULL, ScenarioEpisode, Split
from cybersos.data.split_leakage_gates import validate_scenario_splits


def test_rejects_cross_split_root_and_paraphrase_leakage(full_splits: tuple[ScenarioEpisode, ...]) -> None:
    episode = next(item for item in full_splits if item.split == Split.TRAIN)
    scenario = replace(episode.scenario, scenario_id='leaked-episode')
    leaked = replace(episode, scenario=scenario, split=Split.TEST, paraphrase_id='leaked')
    with pytest.raises(ValueError, match='Cross-split'):
        validate_scenario_splits(full_splits + (leaked,), FULL)


def test_rejects_hidden_state_alias_even_with_different_provenance(full_splits: tuple[ScenarioEpisode, ...]) -> None:
    episode = next(item for item in full_splits if item.split == Split.TRAIN)
    scenario = replace(episode.scenario, scenario_id='aliased-episode', opening_message='New words.')
    root = replace(episode.root, root_id='aliased-root', template_id='renamed-template',
                   root_hash=root_hash(scenario, 'renamed-template'))
    alias = replace(episode, scenario=scenario, root=root, split=Split.TEST, paraphrase_id='alias')
    with pytest.raises(ValueError, match='Cross-split state'):
        validate_scenario_splits(full_splits + (alias,), FULL)


def test_rejects_cross_split_exact_wording_with_other_state(full_splits: tuple[ScenarioEpisode, ...]) -> None:
    train = next(item for item in full_splits if item.split == Split.TRAIN)
    test = next(item for item in full_splits if item.split == Split.TEST)
    corrupted = replace(test, scenario=replace(test.scenario,
                                              opening_message=train.scenario.opening_message))
    episodes = tuple(corrupted if item is test else item for item in full_splits)
    with pytest.raises(ValueError, match='Cross-split paraphrase'):
        validate_scenario_splits(episodes, FULL)


def test_rejects_deduplication_that_drops_a_pair_member(full_splits: tuple[ScenarioEpisode, ...]) -> None:
    paired = next(item for item in full_splits if item.root.pair_id)
    episodes = tuple(item for item in full_splits if item is not paired)
    with pytest.raises(ValueError, match='Counterfactual pair incomplete'):
        validate_scenario_splits(episodes, FULL)


def test_rejects_incorrect_bucket_or_independent_allocations(full_splits: tuple[ScenarioEpisode, ...]) -> None:
    test = next(item for item in full_splits if item.split == Split.TEST)
    allocation = replace(FULL, test_buckets=tuple((bucket, count + (bucket == test.root.bucket))
                                                 for bucket, count in FULL.test_buckets),
                         train=FULL.train - 1)
    with pytest.raises(ValueError, match='allocation mismatch'):
        validate_scenario_splits(full_splits, allocation)
    stripped = tuple(replace(item, root=replace(item.root, independently_constructed=False))
                     for item in full_splits)
    with pytest.raises(ValueError, match='independently constructed'):
        validate_scenario_splits(stripped, FULL)
