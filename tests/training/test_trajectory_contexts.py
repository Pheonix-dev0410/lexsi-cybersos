import pytest

from cybersos.training.trajectory_contexts import DecisionContext, TrajectoryContexts


def test_each_policy_span_keeps_its_own_exact_prefix() -> None:
    registry = TrajectoryContexts()
    first = DecisionContext((1, 2), (3, 4), 0)
    following = DecisionContext((20, 21, 22), (8, 9), 4)
    registry.register([1, 2], [3, 4, 5, 6, 8, 9], [1, 1, 0, 0, 1, 1], [first, following])
    recorded = registry.resolve([1, 2, 3, 4, 5, 6, 8, 9])
    assert recorded.prompt_length == 2
    assert recorded.decisions[1].prefix_ids == (20, 21, 22)
    assert recorded.decisions[1].completion_offset == 4
    assert recorded.decisions[1].prefix_ids != (1, 2, 3, 4, 5, 6)
    with pytest.raises(RuntimeError, match='truncated'):
        registry.resolve([1, 2, 3, 4, 5])


def test_a_new_generation_batch_releases_earlier_contexts() -> None:
    registry = TrajectoryContexts()
    registry.register([1], [2], [1], [DecisionContext((1,), (2,), 0)])
    registry.begin_generation_batch()
    registry.register([5], [6], [1], [DecisionContext((5,), (6,), 0)])
    assert registry.resolve([5, 6]).prompt_length == 1
    with pytest.raises(RuntimeError, match='unknown'):
        registry.resolve([1, 2])


@pytest.mark.parametrize('contexts', [
    [DecisionContext((1, 2), (3,), 0)],
    [DecisionContext((1, 2), (3, 4), 0), DecisionContext((1,), (4,), 1)],
    [DecisionContext((1, 2), (3, 99), 0)],
    [DecisionContext((), (3, 4), 0)],
])
def test_incomplete_or_overlapping_policy_spans_are_rejected(contexts: list[DecisionContext]) -> None:
    with pytest.raises(ValueError, match='Every|overlap|match'):
        TrajectoryContexts().register([1, 2], [3, 4], [1, 1], contexts)


def test_environment_tokens_can_never_be_scored_as_policy_tokens() -> None:
    with pytest.raises(ValueError, match='environment'):
        TrajectoryContexts().register([1], [2, 3], [1, 0], [DecisionContext((1,), (2, 3), 0)])
