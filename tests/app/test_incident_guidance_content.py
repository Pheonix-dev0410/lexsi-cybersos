from dataclasses import replace
from pathlib import Path

import pytest

from cybersos.app.app_assets import AppAssets
from cybersos.app.incident_content import incident_content
from cybersos.app.incident_session import start_incident
from cybersos.app.serving_policy import ServingConfig, ServingModel, load_serving_model
from cybersos.baselines import ObservedStatePlanner
from cybersos.domain import ExecutionStatus, ProviderResponse, SessionMode, TaskOutcome, ToolName
from cybersos.runtime import PolicyTimeoutError
from cybersos.simulator import Observation


def test_incident_asks_one_availability_question_and_isolates_sessions(app_assets: AppAssets) -> None:
    first = start_incident(app_assets, 'account')
    second = start_incident(app_assets, 'account')
    content = incident_content(first)
    assert content.question == 'Is this your own account?'
    assert {value for _, value in content.choices} == {'true', 'false', 'unknown'}
    assert content.instruction == ''
    first.answer('true')
    assert incident_content(first).question == 'Is this account managed by an organization?'
    assert incident_content(second).question == 'Is this your own account?'
    assert not second.environment.observation().facts


def test_unsupported_scope_hands_off_without_recovery_claim(app_assets: AppAssets) -> None:
    session = start_incident(app_assets, 'account')
    session.answer('true')
    session.answer('true')
    session.answer('false')
    session.answer('true')
    content = incident_content(session)
    assert 'administrator' in content.instruction
    session.report('success')
    assert 'handoff required' in incident_content(session).status
    assert 'user-reported' in incident_content(session).status


def test_circular_demo_rejects_the_locked_backup_route(app_assets: AppAssets) -> None:
    session = start_incident(app_assets, 'account', demo_key='circular')
    assert 'outside the locked account' in incident_content(session).question
    session.answer('false')
    content = incident_content(session)
    assert content.instruction == app_assets.registry.rules['official_account_recovery'].user_instruction
    assert content.needs and content.failure
    assert {link.url for link in content.sources} <= {s.url for s in app_assets.registry.sources.values()}
    assert session.environment.mode == SessionMode.INCIDENT_GUIDANCE
    assert not any(e.kind == 'provider_response' for e in session.runner.trace().events)


@pytest.mark.parametrize('response', [ProviderResponse.SUCCESS, ProviderResponse.PENDING_REVIEW])
def test_recovery_submission_is_pending_never_restored(app_assets: AppAssets, response: ProviderResponse) -> None:
    session = start_incident(app_assets, 'account', demo_key='circular')
    session.answer('false')
    session.report(response.value)
    content = incident_content(session)
    assert 'Official recovery pending' in content.status
    assert 'restored' not in content.status.lower()
    assert 'user-reported' in content.status
    assert not session.environment.trusted_snapshot().verified_access_restored
    assert session.runner.trace().outcome == TaskOutcome.INDETERMINATE


def test_user_completion_is_not_verified_and_ignores_provider_script(app_assets: AppAssets) -> None:
    scenario = replace(app_assets.demos['preparedness'], provider_script={'attempt_provider_verification': 'denial'})
    assets = replace(app_assets, demos=app_assets.demos | {'preparedness': scenario})
    session = start_incident(assets, 'account', demo_key='preparedness')
    assert incident_content(session).instruction
    session.report('success')
    content = incident_content(session)
    assert 'User-reported completion' in content.status
    assert 'not independently verified' in content.status
    assert not content.instruction
    assert not session.environment.trusted_snapshot().verified_access_restored
    assert session.runner.trace().outcome == TaskOutcome.INDETERMINATE
    assert not any(e.kind == 'provider_response' for e in session.runner.trace().events)


def test_containment_reacts_to_reported_denial(app_assets: AppAssets) -> None:
    session = start_incident(app_assets, 'exposed', demo_key='containment')
    session.answer('true')
    assert 'Change the exposed password' in incident_content(session).instruction
    session.report('denial')
    assert 'official account recovery' in incident_content(session).instruction.lower()
    assert 'denial' in incident_content(session).status
    assert not any(e.kind == 'provider_response' for e in session.runner.trace().events)


def test_reported_containment_steps_stay_user_reported(app_assets: AppAssets) -> None:
    session = start_incident(app_assets, 'exposed', demo_key='containment')
    session.answer('true')
    for step in session.required_steps:
        assert session.environment.observation().history[-1].data['step_id'] == step
        session.report('success')
    assert 'User-reported completion' in incident_content(session).status
    assert session.environment.trusted_snapshot().completed_steps == frozenset()
    assert not session.environment.trusted_snapshot().verified_access_restored


def test_model_unavailable_at_startup_serves_r_and_says_so(app_assets: AppAssets, tmp_path: Path) -> None:
    serving = load_serving_model(ServingConfig(contract_path=tmp_path / 'missing.yaml'))
    session = start_incident(app_assets, 'account', serving)
    assert 'R · observed-state rule planner' in incident_content(session).policy
    assert 'model unavailable at startup' in incident_content(session).policy
    assert session.runner.trace().decisions[0].action.tool_name == ToolName.ASK_ACCESS


def test_mid_episode_model_timeout_ends_the_session_without_switching_policy(app_assets: AppAssets) -> None:
    planner = ObservedStatePlanner(app_assets.registry)
    calls = []

    def model(observation: Observation) -> str:
        calls.append(observation)
        if len(calls) > 1:
            raise PolicyTimeoutError('generation deadline')
        return planner(observation)

    session = start_incident(app_assets, 'account', ServingModel(model, 'fixture model'))
    session.answer('true')
    content = incident_content(session)
    assert session.environment.done
    assert session.runner.trace().execution_status == ExecutionStatus.TIMEOUT
    assert len(session.runner.trace().decisions) == 1
    assert 'timed out' in content.status and not content.question and not content.instruction
    assert content.policy == 'fixture model'
