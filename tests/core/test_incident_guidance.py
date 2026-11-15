from collections.abc import Callable

import pytest

from cybersos.domain import Action, ProviderResponse, SessionMode, TerminalState, ToolName
from cybersos.runtime import EpisodeRunner
from cybersos.simulator import EpisodeTools, RecoveryEnvironment


def test_incident_questions_never_read_synthetic_answers(make_env: Callable[..., RecoveryEnvironment]) -> None:
    env = make_env(mode=SessionMode.INCIDENT_GUIDANCE, access={'phone_available': True})
    tools = EpisodeTools(env)
    result = tools.ask_access('phone_available')
    assert result.paused and 'value' not in result.data
    assert not env.observation().facts
    assert not tools.ask_access('password_known').ok
    env.report_access(False)
    assert env.observation().observed_facts.value('phone_available') == 'false'
    assert not env.awaiting_report


def test_incident_outcomes_independent_of_provider_script(make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object]) -> None:
    def observe(response: str) -> object:
        env = make_env(facts=backup_facts, mode=SessionMode.INCIDENT_GUIDANCE,
                       script={'use_accessible_backup_code': response})
        result = EpisodeTools(env).simulate_step('use_accessible_backup_code')
        assert not any(e.kind == 'provider_response' for e in env.trusted_snapshot().events)
        return result
    assert observe('success') == observe('denial')


def test_user_report_cannot_claim_verified_restoration(make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object]) -> None:
    env = make_env(facts=backup_facts, mode=SessionMode.INCIDENT_GUIDANCE)
    runner = EpisodeRunner(env)
    action = Action(ToolName.SIMULATE_STEP, {'step_id': 'use_accessible_backup_code'})
    trace = runner.run(lambda observation: action.to_json())
    assert trace.paused and trace.execution_status is None
    report = env.report_step(ProviderResponse.SUCCESS)
    assert report.data['evidence_basis'] == 'user_reported'
    assert env.done and env.execution_status.value == 'finished'
    assert env.terminal_state is None
    assert not env.trusted_snapshot().verified_access_restored
    assert not EpisodeTools(env).finish(TerminalState.SIMULATED_ACCESS_RESTORED, None, ()).ok
    assert env.task_outcome().value == 'indeterminate'


def test_model_cannot_change_incident_mode(make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object]) -> None:
    env = make_env(facts=backup_facts, mode=SessionMode.INCIDENT_GUIDANCE,
                   script={'use_accessible_backup_code': 'success'})
    bad = Action(ToolName.SIMULATE_STEP, {'step_id': 'use_accessible_backup_code', 'mode': 'benchmark'})
    assert not env.execute(bad).ok
    assert env.mode == SessionMode.INCIDENT_GUIDANCE
    with pytest.raises(AttributeError):
        env.mode = SessionMode.BENCHMARK
    assert not env.trusted_snapshot().completed_steps


def test_incident_runner_resumes_after_report(make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object]) -> None:
    env = make_env(facts=backup_facts, mode=SessionMode.INCIDENT_GUIDANCE)
    runner = EpisodeRunner(env)
    action = Action(ToolName.SIMULATE_STEP, {'step_id': 'official_account_recovery'})
    assert runner.run(lambda observation: action.to_json()).paused
    env.report_step(ProviderResponse.PENDING_REVIEW)
    finish = Action(ToolName.FINISH, {'status': 'official_recovery_pending',
                                    'next_step_id': 'official_account_recovery', 'source_ids': ['google_recover']})
    trace = runner.run(lambda observation: finish.to_json())
    assert trace.execution_status.value == 'finished'
    assert not trace.paused
    assert trace.outcome.value == 'indeterminate'
