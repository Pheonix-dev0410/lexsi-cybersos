from collections import Counter
from pathlib import Path

from cybersos.data.decision_gates import (
    DecisionGates, check_counterfactual_preservation, check_export_count,
)
from cybersos.data.decision_rows import Record, Row, row_hash
from cybersos.data.scenario_records import ScenarioEpisode
from cybersos.data.split_artifacts import episode_mapping
from cybersos.playbooks import PlaybookRegistry
from cybersos.serialization import read_json, read_jsonl, write_json, write_jsonl


def curate_decisions(candidate_dir: str | Path, output_dir: str | Path,
                     registry: PlaybookRegistry, training_episodes: tuple[ScenarioEpisode, ...], *,
                     seed: int = 20261113) -> Record:
    from curatorkit import Curator, CuratorConfig

    directory, destination = Path(candidate_dir), Path(output_dir)
    rows = read_jsonl(directory / 'train_candidates.jsonl')
    sidecar = read_json(directory / 'provenance.json')
    trajectories = read_jsonl(directory / 'trajectories.jsonl')
    gates = DecisionGates(trajectories, registry,
                          training_episodes=[episode_mapping(episode) for episode in training_episodes])
    passed: list[Row] = []
    rejected: list[Record] = []
    for number, row in enumerate(rows):
        digest = row_hash(row)
        errors = gates.check(row, sidecar.get(digest, []))
        if errors:
            rejected.append({'candidate_index': number, 'content_hash': digest, 'reasons': errors})
        else:
            passed.append(row)
    transport = destination / 'gated_candidates.jsonl'
    write_jsonl(transport, passed)
    result = Curator(CuratorConfig(
        dataset=str(transport), dedup='exact', clean=False, min_tokens=1, max_tokens=4096,
        export_formats=['alpaca'], output_split=None, output_dir=str(destination),
    )).run()
    exported = read_jsonl(destination / 'sft_alpaca.jsonl')
    check_export_count(len(result.passed), exported)
    exported_hashes = {row_hash(row) for row in exported}
    passed_hashes = {row_hash(row) for row in passed}
    if not exported_hashes <= passed_hashes:
        raise ValueError('curator_modified_content')
    accepted_sidecar = {digest: sidecar[digest] for digest in exported_hashes}
    check_counterfactual_preservation({digest: sidecar[digest] for digest in passed_hashes},
                                      accepted_sidecar)
    curator_reasons = {row_hash({'instruction': sample.instruction, 'input': sample.input or '',
                                'output': sample.output or ''}): sample.rejection_reason
                       for sample in result.rejected}
    consumed: set[str] = set()
    for number, row in enumerate(rows):
        digest = row_hash(row)
        if digest not in passed_hashes:
            continue
        if digest not in exported_hashes or digest in consumed:
            rejected.append({'candidate_index': number, 'content_hash': digest,
                             'reasons': [curator_reasons.get(digest, 'exact_duplicate')]})
        else:
            consumed.add(digest)
    if len(exported) + len(rejected) != len(rows):
        raise ValueError('unaccounted_candidates')
    for row in exported:
        if errors := gates.check(row, accepted_sidecar[row_hash(row)]):
            raise ValueError(f'export_failed_gates:{errors}')
    write_json(destination / 'provenance.json', accepted_sidecar)
    used = {origin['trajectory_id'] for origins in accepted_sidecar.values() for origin in origins}
    write_jsonl(destination / 'trajectories.jsonl',
                (record for record in trajectories if record['trajectory_id'] in used))
    write_jsonl(destination / 'rejections.jsonl', sorted(rejected, key=lambda row: row['candidate_index']))
    manifest = {'seed': seed, 'input_rows': len(rows), 'accepted_rows': len(exported),
                'rejected_rows': len(rejected), 'exported_rows': len(exported),
                'rejection_reasons': dict(Counter(reason for row in rejected for reason in row['reasons'])),
                'dedup': 'exact; full canonical messages in instruction',
                'content_hashes': sorted(exported_hashes), 'source_grounding': 'deterministic registry checks',
                'hallucination_judge': 'not used', 'hallucination_skips': 0,
                'privacy_scan': 'deterministic patterns; synthetic scenarios only',
                'curatorkit_stage_counts': result.stage_counts}
    write_json(destination / 'curation_manifest.json', manifest)
    if not exported:
        raise ValueError('No accepted decisions; see rejections.jsonl')
    return manifest
