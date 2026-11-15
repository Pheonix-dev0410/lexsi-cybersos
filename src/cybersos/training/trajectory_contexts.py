from dataclasses import dataclass
from typing import Iterable


CONTEXT_VERSION = 'cybersos-decision-context-v1'


@dataclass(frozen=True)
class DecisionContext:
    prefix_ids: tuple[int, ...]
    completion_ids: tuple[int, ...]
    completion_offset: int


@dataclass(frozen=True)
class RecordedContexts:
    prompt_length: int
    decisions: tuple[DecisionContext, ...]


class TrajectoryContexts:
    """Generation contexts of the current GRPO generation batch only.

    GRPO finishes every forward pass over a batch before generating the next one, so
    contexts from an earlier batch are released instead of accumulating.
    """

    def __init__(self) -> None:
        self._streams: dict[tuple[int, ...], RecordedContexts] = {}

    def begin_generation_batch(self) -> None:
        self._streams.clear()

    def register(self, prompt_ids: list[int], completion_ids: list[int], mask: list[int],
                 contexts: Iterable[DecisionContext]) -> None:
        stream = tuple(prompt_ids + completion_ids)
        decisions = tuple(contexts)
        if len(mask) != len(completion_ids):
            raise ValueError('Trajectory mask and token stream differ')
        covered: set[int] = set()
        for context in decisions:
            start = context.completion_offset
            end = start + len(context.completion_ids)
            if (start < 0 or end > len(completion_ids) or not context.prefix_ids or
                    tuple(completion_ids[start:end]) != context.completion_ids):
                raise ValueError('Decision context does not match its recorded generated tokens')
            positions = set(range(start, end))
            if covered & positions or any(mask[position] != 1 for position in positions):
                raise ValueError('Decision contexts overlap or include environment tokens')
            covered.update(positions)
        if covered != {index for index, value in enumerate(mask) if value == 1}:
            raise ValueError('Every policy token must have its exact generation context')
        recorded = RecordedContexts(len(prompt_ids), decisions)
        if stream in self._streams and self._streams[stream] != recorded:
            raise ValueError('Identical training tokens have inconsistent generation contexts')
        self._streams[stream] = recorded

    def resolve(self, tokens: Iterable[int]) -> RecordedContexts:
        key = tuple(tokens)
        if key not in self._streams:
            raise RuntimeError('GRPO supplied an unknown or truncated trajectory token stream')
        return self._streams[key]
