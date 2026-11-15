import inspect
from contextlib import contextmanager
from functools import wraps
from typing import Any, Iterator

from cybersos.training.trajectory_contexts import TrajectoryContexts


class TrajectoryForward:
    """Recompute GRPO action logits under the exact compact prefixes used to sample them."""

    def __init__(self, model: Any) -> None:
        self.contexts = TrajectoryContexts()
        self._generating = 0
        original = model.forward
        signature = inspect.signature(original)

        @wraps(original)
        def forward(*args: Any, **kwargs: Any) -> Any:
            if self._generating:
                return original(*args, **kwargs)
            bound = signature.bind_partial(*args, **kwargs)
            values = dict(bound.arguments)
            extras = values.pop('kwargs', {})
            values.update(extras)
            input_ids = values.get('input_ids')
            if input_ids is None:
                raise RuntimeError('Trajectory forward requires token IDs')
            return self._recompute(original, input_ids, values)

        model.forward = forward

    @contextmanager
    def generation(self) -> Iterator[None]:
        self._generating += 1
        try:
            yield
        finally:
            self._generating -= 1

    def _recompute(self, original: Any, input_ids: Any, values: dict[str, Any]) -> Any:
        import torch

        if values.get('labels') is not None or values.get('past_key_values') is not None:
            raise RuntimeError('Trajectory forward supports uncached GRPO log probabilities only')
        attention = values.get('attention_mask')
        if attention is None or attention.ndim != 2:
            raise RuntimeError('GRPO must supply a two-dimensional padding mask')
        logits_to_keep = values.get('logits_to_keep', 0)
        if not isinstance(logits_to_keep, int):
            raise RuntimeError('Unsupported GRPO logits selection')
        rows = []
        last_output = None
        for row, padding in zip(input_ids, attention, strict=True):
            positions = torch.nonzero(padding, as_tuple=False).flatten()
            tokens = row[positions].tolist()
            recorded = self.contexts.resolve(tokens)
            if not recorded.decisions:
                raise RuntimeError('Budget-exhausted rollouts with no policy tokens cannot train')
            result = None
            for context in recorded.decisions:
                sequence = context.prefix_ids + context.completion_ids
                ids = torch.tensor([sequence], dtype=row.dtype, device=row.device)
                arguments = {'input_ids': ids, 'attention_mask': torch.ones_like(ids),
                             'use_cache': False, 'return_dict': True}
                if 'logits_to_keep' in values:
                    arguments['logits_to_keep'] = len(context.completion_ids) + 1
                last_output = original(**arguments)
                count = len(context.completion_ids)
                action_logits = last_output.logits[0, -(count + 1):-1]
                if action_logits.shape[0] != count:
                    raise RuntimeError('Model logits do not align with sampled action tokens')
                if result is None:
                    result = action_logits.new_zeros((input_ids.shape[1], action_logits.shape[-1]))
                start = recorded.prompt_length + context.completion_offset - 1
                indices = positions[start:start + count]
                result = result.index_copy(0, indices, action_logits)
            rows.append(result)
        logits = torch.stack(rows)
        last_output.logits = logits[:, -logits_to_keep:] if logits_to_keep else logits
        return last_output
