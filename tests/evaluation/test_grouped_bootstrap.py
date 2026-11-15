import pytest

from cybersos.evaluation import PairedValue, paired_bootstrap
from cybersos.evaluation.paired_bootstrap import root_resamples


def test_pairs_paraphrases_resample_together_and_seeded() -> None:
    left = [PairedValue(str(i), root, 0, pair) for i, root, pair in
            [(1, 'a', 'pair'), (2, 'a', 'pair'), (3, 'a', None), (4, 'b', None)]]
    right = [PairedValue(v.case_id, v.root_id, 1 if v.root_id == 'a' else 0, v.pair_id) for v in left]
    result = paired_bootstrap(left, right, seed=37, repetitions=100)
    assert result == paired_bootstrap(left, right, seed=37, repetitions=100)
    assert result.difference == .75 and result.lower == 0 and result.upper == 1
    assert result.roots == 2 and result.cases == 4
    for roots in root_resamples(['a', 'b'], repetitions=20, seed=37):
        members = [v.case_id for root in roots for v in left if v.root_id == root]
        assert members.count('1') == members.count('2') == members.count('3')


def test_changed_pair_grouping_and_incomplete_matching_rejected() -> None:
    with pytest.raises(ValueError, match='identical'):
        paired_bootstrap([PairedValue('a', 'r', 0)], [], seed=1)
    left = [PairedValue('a', 'one', 0, 'pair'), PairedValue('b', 'two', 0, 'pair')]
    moved = [PairedValue('a', 'one', 0, 'pair'), PairedValue('b', 'three', 0, 'pair')]
    with pytest.raises(ValueError, match='grouping changed'):
        paired_bootstrap(left, moved, seed=1)


def test_counterfactual_members_on_separate_roots_resample_as_one_unit() -> None:
    left = [PairedValue('eligible', 'root-1', 0, 'pair'), PairedValue('boundary', 'root-2', 0, 'pair'),
            PairedValue('solo', 'root-3', 0)]
    right = [PairedValue('eligible', 'root-1', 1, 'pair'), PairedValue('boundary', 'root-2', 0, 'pair'),
             PairedValue('solo', 'root-3', 0)]
    result = paired_bootstrap(left, right, seed=5, repetitions=200)
    assert result.roots == 2 and result.cases == 3
    # Two units can only resample to means 0, 1/3 or 1/2; resampling three independent roots
    # could also reach 2/3 or 1 by drawing root-1 alone.
    assert (result.lower, result.upper) == (0.0, 0.5)
