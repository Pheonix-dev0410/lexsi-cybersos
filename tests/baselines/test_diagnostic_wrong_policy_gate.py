from collections.abc import Callable

import pytest

from cybersos.baselines import GuidedQuestionnaire, ObservedStatePlanner
from cybersos.data.diagnostic_scenarios import DiagnosticCase
from cybersos.domain import Action, TerminalState, ToolName
from cybersos.oracle import safe_resolution
from cybersos.playbooks import PlaybookRegistry
from cybersos.runtime import EpisodeTrace, Policy
from cybersos.simulator import Observation

CaseRunner = Callable[[DiagnosticCase, Policy], EpisodeTrace]


@pytest.mark.parametrize('policy_type', [GuidedQuestionnaire, ObservedStatePlanner])
def test_reference_baselines_pass_all_reviewed_cases(
        registry: PlaybookRegistry, cases: tuple[DiagnosticCase, ...], run_case: CaseRunner,
        policy_type: type[GuidedQuestionnaire] | type[ObservedStatePlanner]) -> None:
    for case in cases:
        trace = run_case(case, policy_type(registry))
        assert safe_resolution(trace, case.scenario, registry), (
            case.scenario.scenario_id, trace.terminal_state,
            [decision.raw_proposal for decision in trace.decisions])
        attempts = [str(d.action.parameters['step_id']) for d in trace.decisions
                    if d.action and d.action.tool_name == ToolName.SIMULATE_STEP and d.tool_result.ok]
        assert len(attempts) == len(set(attempts))
        assert all('simulate_step:' + step in case.expected_permissible_actions for step in attempts)


def wrong_finish(status: TerminalState) -> str:
    return Action(ToolName.FINISH, {'status': status, 'next_step_id': None, 'source_ids': []}).to_json()


def always_escalate(observation: Observation) -> str:
    if not observation.history:
        return Action(ToolName.SIMULATE_STEP, {'step_id': 'official_account_recovery'}).to_json()
    return Action(ToolName.FINISH, {'status': TerminalState.OFFICIAL_RECOVERY_PENDING,
                                   'next_step_id': 'official_account_recovery',
                                   'source_ids': ['google_recover']}).to_json()


def test_wrong_policies_fail_matched_restoration_objectives(
        registry: PlaybookRegistry, cases: tuple[DiagnosticCase, ...], run_case: CaseRunner) -> None:
    policies = [lambda _: wrong_finish(TerminalState.UNSAFE_REQUEST_DECLINED),
                lambda _: wrong_finish(TerminalState.SIMULATED_ACCESS_RESTORED), always_escalate]
    legitimate = [c for c in cases if c.scenario.objective == TerminalState.SIMULATED_ACCESS_RESTORED]
    assert len(legitimate) >= 6
    for policy in policies:
        assert all(not safe_resolution(run_case(c, policy), c.scenario, registry)
                   for c in legitimate)

