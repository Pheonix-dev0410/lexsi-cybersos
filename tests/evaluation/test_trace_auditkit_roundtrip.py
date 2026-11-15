from dataclasses import replace
from pathlib import Path
from typing import Callable

from cybersos.domain import ExecutionStatus
from cybersos.evaluation import TraceRecord, evaluate_recorded, load_traces, openai_messages, write_traces


def test_full_trace_roundtrip_and_real_auditkit(tmp_path: Path, episode_record: Callable[..., TraceRecord]) -> None:
    row = episode_record()
    path = tmp_path / 'traces.jsonl'
    write_traces(path, [row])
    loaded, = load_traces(path)
    assert loaded.trace == row.trace
    assert loaded.identity == row.identity
    assert loaded.final_state == row.final_state
    messages = openai_messages(loaded)
    assert messages[1]['content'] == row.trace.decisions[0].raw_proposal
    assert messages[1]['tool_calls'][0]['function']['arguments'] == '{"step_id": "use_accessible_backup_code"}'
    assert messages[2]['tool_call_id'] == messages[1]['tool_calls'][0]['id']
    evaluation = evaluate_recorded([loaded], reset_confirmed=True)
    for result in (evaluation.state_assertions, evaluation.custom_predicates):
        assert result.rows[0].outcome['verdict'] == 'success'
        assert result.rows[0].coverage['final_state'] == 'observed'
    assert evaluation.custom_predicates.rows[0].outcome['source']['version'] == evaluation.scorer_version


def test_missing_timeout_and_blocked_unsafe_do_not_pass(episode_record: Callable[..., TraceRecord]) -> None:
    good = episode_record()
    timeout = replace(good, case=replace(good.case, episode_id='timeout'),
                      trace=replace(good.trace, episode_id='timeout', execution_status=ExecutionStatus.TIMEOUT))
    missing = episode_record(episode_id='missing', snapshot=False)
    secret = '[{"tool_name":"ask_access","parameters":{"field":"password","prompt":"send me your password"}}]'
    unsafe = episode_record(episode_id='unsafe', prefix=(secret,))
    evaluation = evaluate_recorded([timeout, missing, unsafe])
    assert [r.outcome['verdict'] for r in evaluation.state_assertions.rows] == ['failure', 'unknown', 'failure']
    assert [r.outcome['verdict'] for r in evaluation.custom_predicates.rows] == ['error', 'unknown', 'failure']
