from dataclasses import replace
from pathlib import Path

import pytest

from cybersos.data.decision_examples import DecisionExamples, save_decision_examples
from cybersos.data.decision_gates import DecisionGates
from cybersos.data.decision_rows import row_hash
from cybersos.data.serving_budgets import ServingBudgets
from cybersos.data.training_file_rendering import render_training_file
from cybersos.playbooks import PlaybookRegistry
from cybersos.policy import render_observation, serialize_prefix
from cybersos.serialization import read_jsonl, write_json, write_jsonl
from fake_tokenizers import CharacterTokenizer


ROOMY = ServingBudgets(actions=12, prompt_tokens=100000, context_tokens=101000,
                       generation_tokens=1000, sequence_tokens=101000)


def prepare_curated(directory: Path, examples: DecisionExamples) -> list[dict[str, str]]:
    save_decision_examples(examples, directory, seed=20261113)
    rows = list({row_hash(row): row for row in examples.rows}.values())
    write_jsonl(directory / 'sft_alpaca.jsonl', rows)
    write_json(directory / 'curation_manifest.json',
               {'accepted_rows': len(rows), 'content_hashes': [row_hash(row) for row in rows]})
    return rows


def test_templates_once_from_replayed_turns_and_keeps_whole_action(
        tmp_path: Path, examples: DecisionExamples, registry: PlaybookRegistry) -> None:
    curated = tmp_path / 'curated'
    rows = prepare_curated(curated, examples)
    output = tmp_path / 'rendered/train_alpaca.jsonl'
    tokenizer = CharacterTokenizer()
    report = render_training_file(curated, output, registry, tokenizer, ROOMY)
    rendered = read_jsonl(output)
    assert len(tokenizer.conversations) == len(rows)
    assert report['accepted_rows'] == report['exported_rows'] == len(rows)
    gates = DecisionGates(list(examples.trajectories), registry)
    for canonical, result in zip(rows, rendered):
        origin = examples.provenance[row_hash(canonical)][0]
        replay = gates.replay(origin['trajectory_id'])
        expected = serialize_prefix(render_observation(replay.observations[origin['turn']]),
                                    CharacterTokenizer(), max_prompt_tokens=ROOMY.prompt_tokens)
        assert result['instruction'] == expected
        assert result['instruction'].count('<system>') == 1
        assert result['input'] == ''
        assert result['output'] == canonical['output'] + tokenizer.eos_token
        assert result['output'].count(tokenizer.eos_token) == 1
    assert any('\n1. ' in row['instruction'] for row in rendered[1:])


@pytest.mark.parametrize('budget', ['prompt_tokens', 'generation_tokens', 'context_tokens'])
def test_budget_failure_rejects_without_truncating_or_publishing(
        tmp_path: Path, examples: DecisionExamples, registry: PlaybookRegistry, budget: str) -> None:
    curated = tmp_path / 'curated'
    prepare_curated(curated, examples)
    output = tmp_path / 'rendered/train_alpaca.jsonl'
    with pytest.raises(ValueError, match='no training file published'):
        render_training_file(curated, output, registry, CharacterTokenizer(),
                             replace(ROOMY, **{budget: 1}))
    assert not output.exists()
    rejections = read_jsonl(output.parent / 'render_rejections.jsonl')
    assert len(rejections) == len(examples.rows)
