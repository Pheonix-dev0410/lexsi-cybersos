from collections.abc import Callable

from cybersos.domain import Action, FactSource, ToolName
from cybersos.runtime import run_episode
from cybersos.simulator import EpisodeTools, RecoveryEnvironment


def test_semantic_correction_invalidates_a_previously_ready_step(
        make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object]) -> None:
    env = make_env(facts=backup_facts, access=backup_facts,
                   corrections=({'field': 'backup_code_accessible_now', 'value': False,
                                 'after_question': 'phone_available'},))
    tools = EpisodeTools(env)
    ready = tools.check_step('use_accessible_backup_code')
    assert ready.data['status'] == 'ready'
    tools.lookup_playbook('google_personal', 'lost_phone')
    assert env.observation().observed_facts.revision == ready.data['revision']
    tools.ask_access('phone_available')
    blocked = tools.check_step('use_accessible_backup_code')
    assert blocked.data['status'] == 'blocked'
    assert blocked.data['revision'] > ready.data['revision']
    assert not tools.simulate_step('use_accessible_backup_code').ok
    history = [f for f in env.observation().fact_history if f.field == 'backup_code_accessible_now']
    assert [f.value.value for f in history] == ['true', 'false']
    assert history[-1].correction and history[-1].source == FactSource.USER_REPORTED
    assert tools.ask_access('backup_code_accessible_now').data['value'] == 'false'


def test_temporary_failure_is_retryable_without_an_agent_error(
        make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object]) -> None:
    env = make_env(facts=backup_facts, script={'use_accessible_backup_code': 'success'},
                   failures=({'tool_name': 'simulate_step', 'step_id': 'use_accessible_backup_code'},))
    actions = iter([
        Action(ToolName.SIMULATE_STEP, {'step_id': 'use_accessible_backup_code'}),
        Action(ToolName.SIMULATE_STEP, {'step_id': 'use_accessible_backup_code'}),
        Action(ToolName.FINISH, {'status': 'simulated_access_restored',
                               'next_step_id': None, 'source_ids': []}),
    ])
    def policy(observation: object) -> str:
        if env.observation().history and not env.observation().history[-1].ok:
            assert not env.trusted_snapshot().attempted_steps
            assert not any(e.kind == 'provider_response' for e in env.trusted_snapshot().events)
        return next(actions).to_json()

    trace = run_episode(policy, env)
    assert trace.decisions[0].tool_result.error == 'temporary_tool_failure'
    assert trace.decisions[0].tool_result.data['retryable'] is True
    assert trace.decisions[1].tool_result.data['provider_response'] == 'success'
    assert all(d.guard_verdict.allowed for d in trace.decisions)
    assert trace.unsafe_proposal_count == 0
    assert trace.execution_status == 'finished' and trace.outcome == 'objective_met'
    assert sum(e.kind == 'provider_response' for e in trace.events) == 1


def test_step_attempt_triggers_correction_even_on_temporary_failure(
        make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object]) -> None:
    env = make_env(facts=backup_facts,
                   failures=({'tool_name': 'simulate_step', 'step_id': 'use_accessible_backup_code'},),
                   corrections=({'field': 'backup_code_accessible_now', 'value': False,
                                 'after_step_id': 'use_accessible_backup_code'},))
    tools = EpisodeTools(env)
    assert not tools.simulate_step('use_accessible_backup_code').ok
    assert tools.check_step('use_accessible_backup_code').data['status'] == 'blocked'
