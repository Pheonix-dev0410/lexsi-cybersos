from pathlib import Path

from cybersos.data.curation_bridge import curate_decisions
from cybersos.data.decision_examples import DecisionExamples, save_decision_examples
from cybersos.data.decision_rows import row_hash
from cybersos.data.scenario_records import ScenarioEpisode
from cybersos.playbooks import PlaybookRegistry
from cybersos.serialization import read_json, read_jsonl, write_jsonl


def test_exact_dedup_keeps_access_flags_and_provenance(
        tmp_path: Path, examples: DecisionExamples,
        training_episodes: tuple[ScenarioEpisode, ...], registry: PlaybookRegistry) -> None:
    candidates, output = tmp_path / 'candidates', tmp_path / 'curated'
    save_decision_examples(examples, candidates, seed=20261113)
    write_jsonl(candidates / 'train_candidates.jsonl', [*examples.rows, examples.rows[0]])
    report = curate_decisions(candidates, output, registry, training_episodes)
    exported = read_jsonl(output / 'sft_alpaca.jsonl')
    assert report['accepted_rows'] == report['exported_rows'] == len(exported)
    assert report['rejection_reasons']['exact_duplicate'] >= 1
    assert report['accepted_rows'] + report['rejected_rows'] == len(examples.rows) + 1
    provenance = read_json(output / 'provenance.json')
    assert {row_hash(row) for row in examples.rows} == set(provenance)
    roots = {origin['root_hash'] for origins in provenance.values() for origin in origins}
    assert len(roots) == 2
    instructions = '\n'.join(row['instruction'] for row in exported)
    assert ' = true [' in instructions
    assert ' = false [' in instructions
