from copy import deepcopy

import pytest

from cybersos.training.batch_alignment import concatenate_aligned_batch_fields


def _output(index: int) -> dict[str, object]:
    return {'prompt_ids': [[index, 0]], 'completion_ids': [[index]], 'logprobs': [[-.2]],
            'env_mask': [[1]], 'trajectories': [index], 'conversations': [[{'role': 'user', 'content': str(index)}]],
            'tools_used': True, 'rewards': [None]}


def test_preserves_outer_order_inner_nesting_and_scalar_fields() -> None:
    combined = concatenate_aligned_batch_fields([_output(1), _output(2), _output(1)])
    assert combined['prompt_ids'] == [[1, 0], [2, 0], [1, 0]]
    assert combined['trajectories'] == [1, 2, 1]
    assert combined['conversations'][1] == [{'role': 'user', 'content': '2'}]
    assert combined['rewards'] == [None, None, None]
    assert combined['tools_used'] is True


@pytest.mark.parametrize('field', ['prompt_ids', 'completion_ids', 'logprobs', 'env_mask',
                                  'trajectories', 'conversations'])
def test_rejects_misaligned_fields(field: str) -> None:
    wrong = deepcopy(_output(1))
    wrong[field] = []
    with pytest.raises(ValueError, match='align|exactly one'):
        concatenate_aligned_batch_fields([wrong])


def test_rejects_different_token_lengths() -> None:
    wrong = _output(1)
    wrong['env_mask'] = [[1, 0]]
    with pytest.raises(ValueError, match='tokens'):
        concatenate_aligned_batch_fields([wrong])
