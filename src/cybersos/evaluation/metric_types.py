from dataclasses import dataclass
from math import floor
from statistics import median
from typing import Sequence


@dataclass(frozen=True)
class Rate:
    numerator: int
    denominator: int
    unknown: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.numerator <= self.denominator or not 0 <= self.unknown <= self.denominator:
            raise ValueError('Invalid metric counts')

    @property
    def value(self) -> float | None:
        return self.numerator / self.denominator if self.denominator else None

    def render(self, *, critical: bool = False) -> str:
        if self.denominator and self.unknown == self.denominator:
            return f'unknown ({self.denominator} cases)'
        if critical and self.numerator == 0:
            result = f'0/{self.denominator} observed on this suite'
        else:
            percent = f'{100 * self.value:.1f}%' if self.value is not None else 'undefined'
            result = f'{self.numerator}/{self.denominator} ({percent})'
        return result + (f'; {self.unknown} unknown' if self.unknown else '')


@dataclass(frozen=True)
class Distribution:
    total: float
    measured: int
    denominator: int
    median: float | None
    p95: float | None


def distribution(values: Sequence[float | int | None]) -> Distribution:
    known = sorted(float(value) for value in values if value is not None)
    p95 = None
    if known:
        position = (len(known) - 1) * .95
        lower = floor(position)
        upper = min(lower + 1, len(known) - 1)
        p95 = known[lower] + (known[upper] - known[lower]) * (position - lower)
    return Distribution(sum(known), len(known), len(values), median(known) if known else None, p95)


@dataclass(frozen=True)
class MetricSummary:
    scheduled: int
    rates: dict[str, Rate]
    execution_statuses: dict[str, int]
    task_outcomes: dict[str, int]
    terminals: dict[str, int]
    diagnostic_flags: dict[str, int]
    policy_counts: dict[str, int]
    system_counts: dict[str, int]
    efficiency: dict[str, Distribution]
