from typing import Callable, Sequence

from cybersos.domain import ToolName
from cybersos.evaluation.metric_types import Distribution, distribution
from cybersos.evaluation.trace_records import TraceRecord


def _allowed_calls(row: TraceRecord) -> int | None:
    return sum(d.guard_verdict.allowed for d in row.trace.decisions) if row.trace else None


def _allowed_questions(row: TraceRecord) -> int | None:
    return sum(d.guard_verdict.allowed and d.action is not None and d.action.tool_name == ToolName.ASK_ACCESS
               for d in row.trace.decisions) if row.trace else None


_MEASURES: dict[str, Callable[[TraceRecord], float | int | None]] = {
    'calls': _allowed_calls,
    'questions': _allowed_questions,
    'turns': lambda row: len(row.trace.decisions) if row.trace else None,
    'generated_tokens': lambda row: row.measurements.output_tokens,
    'input_tokens': lambda row: row.measurements.input_tokens,
    'latency_seconds': lambda row: row.measurements.latency_seconds,
    'generation_calls': lambda row: row.measurements.generation_calls,
    'cache_hits': lambda row: row.measurements.cache_hits,
    'repair_calls': lambda row: row.measurements.repair_calls,
    'repair_seconds': lambda row: row.measurements.repair_seconds,
}


def efficiency(rows: Sequence[TraceRecord]) -> dict[str, Distribution]:
    """Distributions over verified safe successes and over every scheduled case; missing values stay unmeasured."""
    groups = {'successful': [r for r in rows if r.safe_success], 'all': list(rows)}
    return {f'{prefix}_{name}': distribution([measure(r) for r in selected])
            for prefix, selected in groups.items() for name, measure in _MEASURES.items()}


def measured_total(rows: Sequence[TraceRecord], name: str) -> int | None:
    """A total exists only when every case measured it; one unmeasured case makes the total unknown."""
    values = [getattr(row.measurements, name) for row in rows]
    return sum(values) if all(value is not None for value in values) else None
