from pathlib import Path
from types import SimpleNamespace

import pytest

from cybersos.data.serving_budgets import ServingBudgets
from cybersos.serialization import write_jsonl
from cybersos.training import AgentConfig, SFTConfig, load_sft_config
from cybersos.training.residual_target_gate import require_residual_target
from cybersos.training.sft_data_checks import inspect_rendered_training_file, verify_trainer_labels
from fake_tokenizers import CharacterTokenizer


COMPLETION = '[{"tool_name":"ask_access","parameters":{"field":"password_known"}}]<eot>'


@pytest.mark.parametrize('values', [{'batch_size': 0}, {'learning_rate': float('nan')},
                                    {'precision': 'auto'}, {'seed': True}, {'lora_dropout': 1},
                                    {'rendered_dataset_path': 'data/'}, {'batch_size': '1'}])
def test_sft_rejects_invalid_configuration(values: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        SFTConfig(**values)


@pytest.mark.parametrize('values', [{'num_generations': 1}, {'per_device_train_batch_size': 3},
                                    {'seed': False}, {'pilot_scenarios': 31},
                                    {'pilot_scenarios': 65}])
def test_agent_rejects_invalid_configuration(values: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        AgentConfig(**values)


def test_unknown_fields_and_residual_target_gate(tmp_path: Path) -> None:
    config = tmp_path / 'sft.yaml'
    config.write_text('back_end: trl\n')
    with pytest.raises(ValueError, match='Unknown'):
        load_sft_config(config)
    report = tmp_path / 'sft_residuals.md'
    with pytest.raises(ValueError, match='not run'):
        require_residual_target(report)
    report.write_text('Only formatting errors remain.\n')
    with pytest.raises(ValueError, match='Target:'):
        require_residual_target(report)
    report.write_text('Target: Revise the route after denied reauthentication.\n')
    assert 'denied reauthentication' in require_residual_target(report)


def _rendered_file(tmp_path: Path) -> Path:
    path = tmp_path / 'train.jsonl'
    write_jsonl(path, [{'instruction': '<user>observed<assistant>', 'input': '',
                        'output': COMPLETION}] * 5)
    return path


def test_action_label_masks_and_overflow_rejection(tmp_path: Path, budgets: ServingBudgets) -> None:
    path = _rendered_file(tmp_path)
    tokenizer = CharacterTokenizer()
    masks = inspect_rendered_training_file(path, tokenizer, budgets)
    prompt_length = len('<user>observed<assistant>')
    assert len(masks) == 5
    assert masks[0]['labels'][:prompt_length] == [-100] * prompt_length
    assert masks[0]['labels'][prompt_length:] == tokenizer.encode(COMPLETION)
    tight = ServingBudgets(12, prompt_length, 30, budgets.generation_tokens, 30)
    with pytest.raises(ValueError, match='budget'):
        inspect_rendered_training_file(path, tokenizer, tight)


class _Labels(list):
    def tolist(self) -> list[int]:
        return list(self)


def _trainer(examples: list[dict[str, list[int]]], *, shift: int = 0) -> SimpleNamespace:
    def collate(rows: list[dict[str, list[int]]]) -> dict[str, list[_Labels]]:
        row = rows[0]
        labels = [-100] * shift + row['labels'][shift:]
        return {'input_ids': [_Labels(row['input_ids'])], 'labels': [_Labels(labels)]}

    return SimpleNamespace(data_collator=collate, train_dataset=examples)


def test_actual_trainer_label_mask_must_match_rendered_actions(tmp_path: Path,
                                                               budgets: ServingBudgets) -> None:
    expected = inspect_rendered_training_file(_rendered_file(tmp_path), CharacterTokenizer(), budgets)
    verify_trainer_labels(_trainer(expected), expected, tmp_path / 'actual.json')
    assert (tmp_path / 'actual.json').is_file()
    with pytest.raises(RuntimeError, match='differs'):
        verify_trainer_labels(_trainer(expected, shift=len(expected[0]['labels'])), expected,
                              tmp_path / 'masked_action.json')
    with pytest.raises(RuntimeError, match='no collator'):
        verify_trainer_labels(None, expected, tmp_path / 'missing.json')
