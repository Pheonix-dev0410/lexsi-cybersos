from collections import Counter, defaultdict
from pathlib import Path

from cybersos.data.diagnostic_scenarios import load_diagnostic_scenarios
from cybersos.data.scenario_fingerprints import state_hash
from cybersos.data.scenario_records import FULL, ScenarioEpisode, Split
from cybersos.data.split_artifacts import save_scenario_splits
from cybersos.data.split_assignment import build_scenario_splits
from cybersos.project_paths import DIAGNOSTIC_CASES_PATH


def test_splits_are_seed_deterministic_and_root_disjoint(
    full_splits: tuple[ScenarioEpisode, ...], diagnostic_path: Path,
) -> None:
    assert full_splits == build_scenario_splits(diagnostic_path, seed=20261113)
    different = build_scenario_splits(diagnostic_path, seed=20261114)
    assert full_splits != different
    roots = defaultdict(set)
    for episode in full_splits:
        roots[episode.split].add(episode.root.root_hash)
    assert not roots[Split.TRAIN] & roots[Split.TEST]
    assert not roots[Split.TRAIN] & roots[Split.DEV]
    assert not roots[Split.DEV] & roots[Split.TEST]


def test_all_diagnostic_roots_are_kept_in_dev(
    full_splits: tuple[ScenarioEpisode, ...], reduced_splits: tuple[ScenarioEpisode, ...],
    diagnostic_path: Path,
) -> None:
    diagnostics = load_diagnostic_scenarios(diagnostic_path)
    diagnostic_ids = {episode.root.root_id for episode in diagnostics}
    assert len(diagnostics) == 36
    for episodes in (full_splits, reduced_splits):
        assert {episode.split for episode in episodes if episode.root.root_id in diagnostic_ids
                } == {Split.DEV}
        assert len([episode for episode in episodes if 'diagnostic' in episode.root.tags]) == 36


def test_saved_hashes_and_manifest_are_reproducible(
    full_splits: tuple[ScenarioEpisode, ...], tmp_path: Path,
) -> None:
    first = tmp_path / 'first'
    second = tmp_path / 'second'
    save_scenario_splits(full_splits, first, seed=20261113, allocation=FULL)
    save_scenario_splits(full_splits, second, seed=20261113, allocation=FULL)
    assert {path.name for path in first.iterdir()} == {
        'train.jsonl', 'dev.jsonl', 'test.jsonl', 'manifest.json', 'root_hashes.json'}
    for path in first.iterdir():
        assert path.read_bytes() == (second / path.name).read_bytes()


def test_shipped_diagnostic_allocation_is_exact_and_roots_do_not_cross_splits() -> None:
    cases = load_diagnostic_scenarios(DIAGNOSTIC_CASES_PATH)
    assert Counter(case.split for case in cases) == {'prompt_dev': 12, 'diagnostic': 24}
    assert len({case.scenario_root_id for case in cases}) == 36
    assert len({state_hash(case.scenario) for case in cases}) == 36
    assert all(case.scenario.opening_message and case.expected_permissible_actions for case in cases)
