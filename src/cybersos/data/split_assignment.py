import random
from collections import defaultdict
from pathlib import Path

from cybersos.data.diagnostic_scenarios import load_diagnostic_scenarios
from cybersos.data.independent_roots import independent_roots
from cybersos.data.root_generation import generate_roots
from cybersos.data.scenario_fingerprints import paraphrase_hash, state_hash
from cybersos.data.scenario_records import (
    Bucket, PROFILES, ScenarioEpisode, ScenarioRoot, Split, SplitAllocation,
)
from cybersos.data.scenario_wording import render_episodes
from cybersos.data.split_leakage_gates import validate_scenario_splits


def _groups(roots: tuple[ScenarioRoot, ...]) -> list[tuple[ScenarioRoot, ...]]:
    grouped: dict[str, list[ScenarioRoot]] = defaultdict(list)
    for root in roots:
        grouped[root.pair_id or root.root_id].append(root)
    return [tuple(group) for group in grouped.values()]


def _allocation(total: int) -> dict[Bucket, int]:
    routine = total // 4 * 2
    remaining = total - routine
    counts = [remaining // 3 + (index < remaining % 3) for index in range(3)]
    return dict(zip(Bucket, (routine, *counts)))


def assign_roots(roots: tuple[ScenarioRoot, ...], *, seed: int,
                 allocation: SplitAllocation, diagnostics: tuple[ScenarioEpisode, ...]
                 ) -> tuple[tuple[ScenarioRoot, Split], ...]:
    """Allocate indivisible root/pair groups before any opening paraphrases are rendered."""
    if len(diagnostics) > allocation.dev:
        raise ValueError('Diagnostic episodes exceed the declared development allocation')
    states = {root.root_id: state_hash(root.scenario) for root in roots}
    reserved = {state_hash(episode.scenario) for episode in diagnostics}
    reserved_ids = {episode.root.root_id for episode in diagnostics}
    groups = [group for group in _groups(roots) if all(
        states[root.root_id] not in reserved and root.root_id not in reserved_ids
        for root in group)]
    rng = random.Random(seed)
    rng.shuffle(groups)
    groups.sort(key=lambda group: not group[0].independently_constructed)
    selected: list[tuple[ScenarioRoot, Split]] = []
    used_states = set(reserved)
    used_roots = set(reserved_ids)

    def take(split: Split, desired: dict[Bucket, int]) -> None:
        for bucket, count in desired.items():
            candidates = [group for group in groups if group[0].bucket == bucket]
            # Round-robin templates ensures small families survive the larger buckets.
            by_template: dict[str, list[tuple[ScenarioRoot, ...]]] = defaultdict(list)
            for group in candidates:
                by_template[group[0].template_id].append(group)
            ordered = []
            while any(by_template.values()):
                for queue in by_template.values():
                    if queue:
                        ordered.append(queue.pop(0))
            ordered.sort(key=lambda group: not group[0].independently_constructed)
            for group in ordered:
                if split != Split.TEST and any(root.independently_constructed for root in group):
                    continue
                hashes = {states[root.root_id] for root in group}
                if any(root.root_id in used_roots for root in group) or hashes & used_states:
                    continue
                if len(group) > count:
                    continue
                selected.extend((root, split) for root in group)
                used_roots.update(root.root_id for root in group)
                used_states.update(hashes)
                count -= len(group)
                if count == 0:
                    break
            if count:
                raise ValueError(f'Insufficient disjoint {bucket} roots for {split}: missing {count}')

    take(Split.TEST, dict(allocation.test_buckets))
    take(Split.DEV, _allocation(allocation.dev - len(diagnostics)))
    take(Split.TRAIN, _allocation(allocation.train))
    return tuple(selected)


def _render_without_cross_split_wording(assignments: tuple[tuple[ScenarioRoot, Split], ...], *,
                                        seed: int, attempts: int = 100) -> tuple[ScenarioEpisode, ...]:
    """Redraw wording until no opening message is shared across splits.

    Openings state only a few facts, so different hidden states can be worded alike.
    """
    owners: dict[str, Split] = {}
    episodes: list[ScenarioEpisode] = []
    for root, split in assignments:
        for attempt in range(attempts):
            rendered = render_episodes(root, split, seed=seed, attempt=attempt)
            keys = [paraphrase_hash(episode.scenario.opening_message) for episode in rendered]
            if all(owners.get(key, split) == split for key in keys):
                break
        else:
            raise ValueError(f'No split-unique wording for {root.root_id}')
        owners.update(dict.fromkeys(keys, split))
        episodes.extend(rendered)
    return tuple(episodes)


def build_scenario_splits(diagnostic_path: str | Path, *, seed: int,
                          profile: str = 'full') -> tuple[ScenarioEpisode, ...]:
    if profile not in PROFILES:
        raise ValueError(f'Unknown split profile: {profile}')
    allocation = PROFILES[profile]
    diagnostics = tuple(case.episode for case in load_diagnostic_scenarios(diagnostic_path))
    roots = independent_roots() + generate_roots()
    assignments = assign_roots(roots, seed=seed, allocation=allocation, diagnostics=diagnostics)
    episodes = diagnostics + _render_without_cross_split_wording(assignments, seed=seed)
    validate_scenario_splits(episodes, allocation, diagnostics=diagnostics)
    return episodes
