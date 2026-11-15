from collections import Counter, defaultdict
from dataclasses import dataclass

from cybersos.data.scenario_fingerprints import paraphrase_hash, root_hash, state_hash, state_mapping
from cybersos.data.scenario_records import (
    Bucket, ScenarioEpisode, Split, SplitAllocation,
)


@dataclass(frozen=True)
class SplitGateReport:
    episode_counts: tuple[tuple[str, int], ...]
    test_bucket_counts: tuple[tuple[str, int], ...]
    independent_test_episodes: int
    independent_test_roots: int
    externally_reviewed_test_roots: int


def _check_pairs(episodes: tuple[ScenarioEpisode, ...]) -> None:
    pairs: dict[str, list[ScenarioEpisode]] = defaultdict(list)
    for episode in episodes:
        if episode.root.pair_id:
            pairs[episode.root.pair_id].append(episode)
        elif episode.root.bucket == Bucket.ROUTINE and 'diagnostic' not in episode.root.tags:
            raise ValueError('Routine scenario is missing its counterfactual pair')
    for pair_id, members in pairs.items():
        branches: dict[str, list[ScenarioEpisode]] = defaultdict(list)
        for member in members:
            branches[member.root.root_hash].append(member)
        if len(branches) != 2 or len({member.split for member in members}) != 1:
            raise ValueError(f'Counterfactual pair incomplete or split: {pair_id}')
        first, second = (branch[0] for branch in branches.values())
        if len({len(branch) for branch in branches.values()}) != 1:
            raise ValueError(f'Counterfactual pair collapsed by deduplication: {pair_id}')
        field = first.root.changed_field
        if field is None or field != second.root.changed_field:
            raise ValueError(f'Counterfactual pair missing changed field: {pair_id}')
        left, right = state_mapping(first.scenario), state_mapping(second.scenario)
        changed = {key for key in left['access'].keys() | right['access'].keys()
                   if left['access'].get(key) != right['access'].get(key)}
        if changed != {field}:
            raise ValueError(f'Counterfactual pair must change exactly one access fact: {pair_id}')
        for record in (left, right):
            record['access'].pop(field)
        if left != right:
            raise ValueError(f'Counterfactual pair changes additional structure: {pair_id}')


def validate_scenario_splits(episodes: tuple[ScenarioEpisode, ...], allocation: SplitAllocation,
                             *, diagnostics: tuple[ScenarioEpisode, ...] = ()) -> SplitGateReport:
    owners: dict[tuple[str, str], Split] = {}
    identifiers: set[str] = set()
    root_contents: dict[str, str] = {}
    for episode in episodes:
        root = episode.root
        if episode.scenario.scenario_id in identifiers:
            raise ValueError('Duplicate episode identifier')
        identifiers.add(episode.scenario.scenario_id)
        digest = root_hash(episode.scenario, root.template_id)
        if digest != root.root_hash or root_hash(root.scenario, root.template_id) != digest:
            raise ValueError('Scenario content disagrees with its saved root hash')
        if root_contents.setdefault(root.root_id, digest) != digest:
            raise ValueError('One root ID refers to different scenario states')
        keys = {'root_id': root.root_id, 'root_hash': root.root_hash,
                'state': state_hash(episode.scenario), 'paraphrase_id': episode.paraphrase_id}
        if episode.scenario.opening_message.strip():
            keys['paraphrase'] = paraphrase_hash(episode.scenario.opening_message)
        for kind, value in keys.items():
            previous = owners.setdefault((kind, value), episode.split)
            if previous != episode.split:
                raise ValueError(f'Cross-split {kind} leakage: {value}')
    _check_pairs(episodes)
    counts = Counter(episode.split for episode in episodes)
    if counts != {Split.TRAIN: allocation.train, Split.DEV: allocation.dev,
                  Split.TEST: allocation.test}:
        raise ValueError(f'Split episode allocation mismatch: {dict(counts)}')
    buckets = Counter(episode.root.bucket for episode in episodes if episode.split == Split.TEST)
    if buckets != dict(allocation.test_buckets):
        raise ValueError(f'Test bucket allocation mismatch: {dict(buckets)}')
    diagnostic_ids = {episode.root.root_id for episode in diagnostics}
    diagnostic_states = {state_hash(episode.scenario) for episode in diagnostics}
    for episode in episodes:
        if (episode.root.root_id in diagnostic_ids or state_hash(episode.scenario) in diagnostic_states
                or 'diagnostic' in episode.root.tags) and episode.split != Split.DEV:
            raise ValueError('Diagnostic roots must remain in development')
    dev_ids = {episode.scenario.scenario_id for episode in episodes if episode.split == Split.DEV}
    if not {episode.scenario.scenario_id for episode in diagnostics} <= dev_ids:
        raise ValueError('Development split is missing diagnostic episodes')
    independent = [episode for episode in episodes if episode.split == Split.TEST
                   and episode.root.independently_constructed]
    independent_roots = {episode.root.root_hash for episode in independent}
    if len(independent_roots) < allocation.minimum_independent_roots:
        raise ValueError('Insufficient independently constructed test roots')
    reviewed = {episode.root.root_hash for episode in episodes if episode.split == Split.TEST
                and episode.root.externally_reviewed}
    return SplitGateReport(tuple((split.value, counts[split]) for split in Split),
                           tuple((bucket.value, buckets[bucket]) for bucket in Bucket),
                           len(independent), len(independent_roots), len(reviewed))
