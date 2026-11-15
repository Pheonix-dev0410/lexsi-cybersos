from collections import defaultdict
from dataclasses import dataclass
from random import Random
from typing import Callable, Sequence

from cybersos.evaluation.trace_records import TraceRecord


@dataclass(frozen=True)
class PairedValue:
    case_id: str
    root_id: str
    value: float
    pair_id: str | None = None


@dataclass(frozen=True)
class BootstrapResult:
    difference: float
    lower: float
    upper: float
    confidence: float
    roots: int
    cases: int
    repetitions: int
    seed: int


def root_resamples(root_ids: Sequence[str], *, repetitions: int, seed: int) -> tuple[tuple[str, ...], ...]:
    roots = sorted(set(root_ids))
    if not roots or repetitions < 1:
        raise ValueError('Nonempty roots and positive repetitions required')
    random = Random(seed)
    return tuple(tuple(random.choices(roots, k=len(roots))) for _ in range(repetitions))


def _resampling_clusters(values: Sequence[PairedValue]) -> dict[str, str]:
    """Map each root to its resampling unit: roots joined by a counterfactual pair move together.

    Pair members are built as separate roots, but their outcomes are deliberately correlated;
    resampling them independently would understate the interval.
    """
    parent = {value.root_id: value.root_id for value in values}

    def find(root: str) -> str:
        while parent[root] != root:
            root = parent[root]
        return root

    first_root_of_pair: dict[str, str] = {}
    for value in values:
        if value.pair_id:
            anchor = first_root_of_pair.setdefault(value.pair_id, value.root_id)
            parent[find(value.root_id)] = find(anchor)
    return {root: find(root) for root in parent}


def paired_bootstrap(left: Sequence[PairedValue], right: Sequence[PairedValue], *,
                     seed: int, repetitions: int = 2000, confidence: float = .95) -> BootstrapResult:
    """Return right minus left, resampling complete scenario roots (pairs kept together)."""
    left_by_case, right_by_case = {v.case_id: v for v in left}, {v.case_id: v for v in right}
    if (not left_by_case or left_by_case.keys() != right_by_case.keys() or
            len(left_by_case) != len(left) or len(right_by_case) != len(right)):
        raise ValueError('Checkpoints require identical, unique scheduled case IDs')
    if not 0 < confidence < 1:
        raise ValueError('Confidence must lie between zero and one')
    for key, value in left_by_case.items():
        other = right_by_case[key]
        if (value.root_id, value.pair_id) != (other.root_id, other.pair_id):
            raise ValueError('Scenario grouping changed between checkpoints')
    cluster = _resampling_clusters(left)
    groups: dict[str, list[float]] = defaultdict(list)
    for key, value in left_by_case.items():
        groups[cluster[value.root_id]].append(right_by_case[key].value - value.value)
    samples = []
    for roots in root_resamples(tuple(groups), repetitions=repetitions, seed=seed):
        differences = [value for root in roots for value in groups[root]]
        samples.append(sum(differences) / len(differences))
    samples.sort()
    tail = (1 - confidence) / 2
    lower = samples[int(tail * (repetitions - 1))]
    upper = samples[int((1 - tail) * (repetitions - 1))]
    differences = [value for values in groups.values() for value in values]
    return BootstrapResult(sum(differences) / len(differences), lower, upper, confidence,
                           len(groups), len(left_by_case), repetitions, seed)


def compare_checkpoints(left: Sequence[TraceRecord], right: Sequence[TraceRecord], *,
                        seed: int, metric: Callable[[TraceRecord], float] = lambda r: float(r.safe_success),
                        repetitions: int = 2000) -> BootstrapResult:
    contracts = {r.identity.contract_hash for r in (*left, *right)}
    if len(contracts) != 1:
        raise ValueError('Checkpoint comparison requires one frozen serving contract')
    def values(records: Sequence[TraceRecord]) -> list[PairedValue]:
        return [PairedValue(r.case.episode_id, r.case.root_id, metric(r), r.case.pair_id)
                for r in records]
    return paired_bootstrap(values(left), values(right), seed=seed, repetitions=repetitions)
