from pathlib import Path
from typing import Any

from cybersos.data.decision_rows import require_alpaca_row
from cybersos.data.serving_budgets import ServingBudgets
from cybersos.data.token_boundaries import split_token_ids
from cybersos.safety import parse_action
from cybersos.serialization import read_jsonl, write_json


LabelExample = dict[str, list[int]]
INSPECTED_ROWS = 5


def inspect_rendered_training_file(path: str | Path, tokenizer: Any,
                                   budgets: ServingBudgets) -> list[LabelExample]:
    """Reject overflow before TRL can truncate; return the first rows' expected label masks."""
    source = Path(path)
    if not source.is_file() or source.suffix != '.jsonl':
        raise ValueError('Expected one rendered training JSONL file')
    end = tokenizer.eos_token
    if not end or len(tokenizer.encode(end, add_special_tokens=False)) != 1:
        raise ValueError('Tokenizer needs a single end-of-turn token')
    rows = read_jsonl(source)
    if len(rows) < INSPECTED_ROWS:
        raise ValueError('At least five rendered decisions are required for label inspection')
    inspected: list[LabelExample] = []
    for number, row in enumerate(rows, 1):
        try:
            require_alpaca_row(row)
            prompt, completion = row['instruction'], row['output']
            if not completion.endswith(end) or completion.count(end) != 1:
                raise ValueError('must end with exactly one end-of-turn token')
            if parse_action(completion[:-len(end)]).action is None:
                raise ValueError('completion is not exactly one action')
            prompt_ids, completion_ids = split_token_ids(prompt, completion, tokenizer, budgets)
        except ValueError as error:
            raise ValueError(f'Row {number}: {error}') from error
        if len(inspected) < INSPECTED_ROWS:
            inspected.append({'input_ids': prompt_ids + completion_ids,
                              'labels': [-100] * len(prompt_ids) + completion_ids})
    return inspected


def verify_trainer_labels(trainer: Any, expected: list[LabelExample], path: str | Path) -> None:
    """Compare the built TRL trainer's real collated batches with the rendered label masks."""
    collator = getattr(trainer, 'data_collator', None)
    dataset = getattr(trainer, 'train_dataset', None)
    if collator is None or dataset is None or len(dataset) < len(expected) or not expected:
        raise RuntimeError('Built trainer has no collator or training rows to inspect')
    actual = []
    for index, example in enumerate(expected):
        batch = collator([dataset[index]])
        ids, labels = batch['input_ids'][0].tolist(), batch['labels'][0].tolist()
        if ids != example['input_ids'] or labels != example['labels']:
            raise RuntimeError('Actual TRL label mask or token sequence differs from rendered action')
        actual.append({'input_ids': ids, 'labels': labels})
    write_json(path, actual)
