from dataclasses import dataclass
from enum import StrEnum

from cybersos.domain import AccessField, Scenario


class Bucket(StrEnum):
    ROUTINE = 'routine_access_constraints'
    BOUNDARY = 'pending_blocked_admin'
    UNAUTHORIZED = 'unauthorized_bypass'
    ROBUSTNESS = 'misleading_evidence_robustness'


class Split(StrEnum):
    TRAIN = 'train'
    DEV = 'dev'
    TEST = 'test'


@dataclass(frozen=True)
class ScenarioRoot:
    scenario: Scenario
    root_id: str
    root_hash: str
    template_id: str
    bucket: Bucket
    tags: tuple[str, ...]
    pair_id: str | None = None
    changed_field: AccessField | None = None
    restoration_eligible: bool = False
    independently_constructed: bool = False
    externally_reviewed: bool = False


@dataclass(frozen=True)
class ScenarioEpisode:
    scenario: Scenario
    root: ScenarioRoot
    split: Split
    paraphrase_id: str


@dataclass(frozen=True)
class SplitAllocation:
    profile: str
    train: int
    dev: int
    test_buckets: tuple[tuple[Bucket, int], ...]
    minimum_independent_roots: int = 30

    @property
    def test(self) -> int:
        return sum(count for _, count in self.test_buckets)


FULL = SplitAllocation('full', 400, 60, tuple(zip(Bucket, (120, 40, 40, 40))))
REDUCED = SplitAllocation('reduced', 240, 40, tuple(zip(Bucket, (60, 20, 20, 20))))
PROFILES = {'full': FULL, 'reduced': REDUCED}
