from pathlib import Path
from typing import Any

from cybersos.data.scenario_fingerprints import scenario_mapping
from cybersos.data.scenario_records import ScenarioEpisode, Split, SplitAllocation
from cybersos.data.split_leakage_gates import validate_scenario_splits
from cybersos.serialization import canonical_json_sha256, to_json_value, write_json, write_jsonl


def episode_mapping(episode: ScenarioEpisode) -> dict[str, Any]:
    root = episode.root
    return {
        'scenario': scenario_mapping(episode.scenario), 'split': episode.split.value,
        'root_id': root.root_id, 'root_hash': root.root_hash, 'template_id': root.template_id,
        'bucket': root.bucket.value, 'tags': root.tags, 'pair_id': root.pair_id,
        'changed_field': root.changed_field, 'restoration_eligible': root.restoration_eligible,
        'independently_constructed': root.independently_constructed,
        'externally_reviewed': root.externally_reviewed, 'paraphrase_id': episode.paraphrase_id,
    }


def save_scenario_splits(episodes: tuple[ScenarioEpisode, ...], output_dir: str | Path, *,
                         seed: int, allocation: SplitAllocation) -> Path:
    """Save evaluator-only JSONL and deterministic root/file hashes after validation."""
    report = validate_scenario_splits(episodes, allocation)
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    files = {}
    for split in Split:
        rows = [episode_mapping(episode) for episode in episodes if episode.split == split]
        rows.sort(key=lambda row: row['scenario']['scenario_id'])
        name = f'{split.value}.jsonl'
        write_jsonl(directory / name, rows)
        files[name] = canonical_json_sha256(rows)
    root_rows = {episode.root.root_id: {'root_hash': episode.root.root_hash,
                                      'split': episode.split.value,
                                      'template_id': episode.root.template_id}
                 for episode in episodes}
    write_json(directory / 'root_hashes.json', root_rows)
    manifest = {'schema_version': 1, 'visibility': 'evaluator_only', 'seed': seed,
                'allocation': to_json_value(allocation),
                'gates': to_json_value(report), 'canonical_content_hashes': files,
                'root_assignments_hash': canonical_json_sha256(root_rows),
                'construction': 'deterministic templates plus separately authored test structures',
                'external_review': 'none claimed',
                'robustness_events': 'simulator semantic corrections and retryable temporary tool failures'}
    path = directory / 'manifest.json'
    write_json(path, manifest)
    return path
