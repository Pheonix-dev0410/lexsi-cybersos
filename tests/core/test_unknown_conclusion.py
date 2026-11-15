from collections.abc import Callable

from cybersos.domain import Action, TerminalState, ToolName
from cybersos.runtime import run_episode
from cybersos.simulator import EpisodeTools, RecoveryEnvironment


def test_unknown_after_asking_supports_an_honest_finish(
        make_env: Callable[..., RecoveryEnvironment]) -> None:
    env = make_env(facts={'safe_other_device': True}, access={'account_owner': True},
                   answers={'account_owner': 'unknown'})
    tools = EpisodeTools(env)
    assert TerminalState.NO_SUPPORTED_PATH_KNOWN not in env.guard_context().supported_terminals
    assert tools.ask_access('account_owner').data['value'] == 'unknown'
    assert TerminalState.NO_SUPPORTED_PATH_KNOWN in env.guard_context().supported_terminals
    trace = run_episode(lambda observation: Action(ToolName.FINISH, {
        'status': TerminalState.NO_SUPPORTED_PATH_KNOWN, 'next_step_id': None, 'source_ids': [],
    }).to_json(), env)
    assert trace.terminal_state == TerminalState.NO_SUPPORTED_PATH_KNOWN
    assert trace.execution_status == 'finished'
    assert trace.outcome == 'objective_met'
    assert trace.unsafe_proposal_count == 0


def test_unknown_answer_does_not_hide_an_established_route(
        make_env: Callable[..., RecoveryEnvironment], backup_facts: dict[str, object]) -> None:
    env = make_env(facts=backup_facts, answers={'independent_passkey_available': 'unknown'})
    EpisodeTools(env).ask_access('independent_passkey_available')
    assert TerminalState.NO_SUPPORTED_PATH_KNOWN not in env.guard_context().supported_terminals
