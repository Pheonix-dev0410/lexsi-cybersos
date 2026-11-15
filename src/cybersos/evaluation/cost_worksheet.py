from dataclasses import dataclass
from math import isfinite
from typing import Mapping

from cybersos.evaluation.metric_types import MetricSummary


@dataclass(frozen=True)
class CostWorksheet:
    deployment: str
    total_serving_cost: float | None
    scheduled: int
    attempted: int
    not_run: int
    safe_successes: int
    cost_per_attempt: float | None
    cost_per_safe_success: float | None

    def render(self) -> str:
        def money(value: float | None) -> str:
            return 'undefined' if value is None else f'{value:.6f}'
        total = 'not supplied' if self.total_serving_cost is None else money(self.total_serving_cost)
        return (f'{self.deployment}: scheduled {self.scheduled}; attempted {self.attempted}; '
                f'not run {self.not_run}; safe successes {self.safe_successes}; total serving cost {total}; '
                f'per attempted task {money(self.cost_per_attempt)}; '
                f'per successful safe task {money(self.cost_per_safe_success)}')


def serving_cost(deployment: str, summary: MetricSummary, total_serving_cost: float | None) -> CostWorksheet:
    """Price the same workload per attempt and per safe success; zero successes leave the latter undefined."""
    if total_serving_cost is not None and (not isfinite(total_serving_cost) or total_serving_cost < 0):
        raise ValueError('Serving cost must be finite and nonnegative')
    not_run = summary.execution_statuses['not_run']
    attempted = summary.scheduled - not_run
    safe = summary.system_counts['verified_safe_resolutions']
    known = total_serving_cost is not None
    return CostWorksheet(deployment, total_serving_cost, summary.scheduled, attempted, not_run, safe,
                         total_serving_cost / attempted if known and attempted else None,
                         total_serving_cost / safe if known and safe else None)


def evaluation_seconds(case_count: int, mean_seconds_per_checkpoint: Mapping[str, float]) -> float:
    """Pilot means must include loading, prompt processing, all turns and retries."""
    if case_count < 0 or not mean_seconds_per_checkpoint:
        raise ValueError('Case count and checkpoint pilot timings are required')
    if any(not isfinite(value) or value < 0 for value in mean_seconds_per_checkpoint.values()):
        raise ValueError('Pilot timings must be finite and nonnegative')
    return case_count * sum(mean_seconds_per_checkpoint.values())
