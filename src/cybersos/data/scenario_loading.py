from pathlib import Path

from cybersos.data.decision_rows import Record
from cybersos.data.scenario_records import PROFILES, Bucket, ScenarioEpisode, ScenarioRoot, Split
from cybersos.data.split_leakage_gates import validate_scenario_splits
from cybersos.domain import AccessField, Scenario
from cybersos.serialization import read_jsonl


def root_from_mapping(scenario: Scenario, row: Record, *, tags: tuple[str, ...] = ()) -> ScenarioRoot:
    return ScenarioRoot(
        scenario, row['root_id'], row['root_hash'], row['template_id'], Bucket(row['bucket']),
        tuple(dict.fromkeys((*row['tags'], *tags))), pair_id=row.get('pair_id'),
        changed_field=AccessField(row['changed_field']) if row.get('changed_field') else None,
        restoration_eligible=row.get('restoration_eligible', False),
        independently_constructed=row.get('independently_constructed', False),
        externally_reviewed=row.get('externally_reviewed', False))


def episode_from_mapping(row: Record) -> ScenarioEpisode:
    scenario = Scenario.from_mapping(row['scenario'])
    return ScenarioEpisode(scenario, root_from_mapping(scenario, row), Split(row['split']),
                           row['paraphrase_id'])


def load_scenario_splits(directory: str | Path) -> tuple[ScenarioEpisode, ...]:
    return tuple(episode_from_mapping(row) for split in Split
                 for row in read_jsonl(Path(directory) / f'{split.value}.jsonl'))


def load_training_episodes(directory: str | Path, profile: str) -> tuple[ScenarioEpisode, ...]:
    """Training episodes of a saved corpus whose splits pass every leakage gate."""
    episodes = load_scenario_splits(directory)
    validate_scenario_splits(episodes, PROFILES[profile])
    return tuple(episode for episode in episodes if episode.split == Split.TRAIN)
