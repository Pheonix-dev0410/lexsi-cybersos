from pathlib import Path
from typing import Any, Iterable

from cybersos.domain import Action, ExecutionStatus, SessionMode, TaskOutcome, TerminalState, ToolName
from cybersos.runtime import DecisionTrace, EpisodeTrace
from cybersos.safety import GuardVerdict, Violation, ViolationKind
from cybersos.serialization import read_jsonl, write_jsonl
from cybersos.simulator import Event, ToolResult
from cybersos.evaluation.trace_records import (
    Adjudication, CaseInfo, Measurements, RunIdentity, TraceRecord,
)


def _decision(data: dict[str, Any]) -> DecisionTrace:
    action = data['action']
    verdict = data['guard_verdict']
    result = data['tool_result']
    return DecisionTrace(data['turn'], data['raw_proposal'],
                         Action(**action) if action else None, data['parse_error'],
                         GuardVerdict(verdict['allowed'], tuple(
                             Violation(ViolationKind(v['kind']), v['detail'])
                             for v in verdict['violations'])),
                         ToolResult(ToolName(result['tool_name']), result['ok'], result['data'],
                                    result['error'], result['paused']))


def _trace(raw: dict[str, Any]) -> EpisodeTrace:
    return EpisodeTrace(
        raw['episode_id'], raw['scenario_id'], SessionMode(raw['mode']),
        tuple(_decision(item) for item in raw['decisions']),
        tuple(Event(**item) for item in raw['events']),
        TerminalState(raw['terminal_state']) if raw['terminal_state'] else None,
        ExecutionStatus(raw['execution_status']) if raw['execution_status'] else None,
        TaskOutcome(raw['outcome']), raw['paused'], raw['error'], raw['observation_mode'])


def record_from_mapping(data: dict[str, Any]) -> TraceRecord:
    if data.get('schema_version') != 'cybersos.trace.v1':
        raise ValueError('Unsupported trace schema')
    case = dict(data['case'])
    case['expected_terminal'] = (TerminalState(case['expected_terminal'])
                                 if case['expected_terminal'] else None)
    case['slices'] = tuple(case['slices'])
    adjudication = dict(data['adjudication'])
    for key in ('recommendation_support', 'diagnostic_flags'):
        adjudication[key] = tuple(adjudication[key])
    return TraceRecord(RunIdentity(**data['identity']), CaseInfo(**case),
                       _trace(data['trace']) if data['trace'] is not None else None,
                       data['final_state'], Measurements(**data['measurements']),
                       Adjudication(**adjudication), model_messages=tuple(data.get('model_messages', ())))


def write_traces(path: str | Path, records: Iterable[TraceRecord]) -> None:
    write_jsonl(path, records)


def load_traces(path: str | Path) -> tuple[TraceRecord, ...]:
    return tuple(record_from_mapping(row) for row in read_jsonl(path))
