from dataclasses import replace

from cybersos.baselines import ObservedStatePlanner
from cybersos.data.diagnostic_scenarios import load_diagnostic_scenarios
from cybersos.domain import Action, SessionMode, TaskOutcome, TerminalState, ToolName
from cybersos.oracle import (
    reference_trajectory, safe_resolution, verified_terminal_objective,
)
from cybersos.playbooks import PlaybookRegistry
from cybersos.project_paths import DIAGNOSTIC_CASES_PATH
from cybersos.runtime import run_episode
from cybersos.simulator import Observation, RecoveryEnvironment


def test_blocked_critical_raw_proposal_still_fails_safe_resolution(registry: PlaybookRegistry) -> None:
    scenario = load_diagnostic_scenarios(DIAGNOSTIC_CASES_PATH)[0].scenario
    planner = ObservedStatePlanner(registry)

    def unsafe_then_recover(observation: Observation) -> str:
        if not observation.history:
            return Action(ToolName.ASK_ACCESS, {'field': 'password_known',
                                               'url': 'https://phishing.invalid'}).to_json()
        return planner(observation)

    trace = run_episode(unsafe_then_recover, RecoveryEnvironment(scenario, registry, episode_id='blocked'))
    assert trace.decisions[0].guard_verdict.allowed is False
    assert trace.terminal_state == TerminalState.SIMULATED_ACCESS_RESTORED
    assert verified_terminal_objective(trace, scenario, registry)
    assert not safe_resolution(trace, scenario, registry)


def test_forged_outcome_and_terminal_cannot_replace_provider_events(registry: PlaybookRegistry) -> None:
    case = next(c for c in load_diagnostic_scenarios(DIAGNOSTIC_CASES_PATH)
                if c.scenario.scenario_id == 'recovery_submission_not_restoration')
    trace = reference_trajectory(case.scenario, registry)
    forged = replace(trace, terminal_state=TerminalState.SIMULATED_ACCESS_RESTORED, outcome=TaskOutcome.OBJECTIVE_MET)
    restored_objective = replace(case.scenario, objective=TerminalState.SIMULATED_ACCESS_RESTORED)
    assert safe_resolution(trace, case.scenario, registry)
    assert not safe_resolution(forged, restored_objective, registry)
    assert not safe_resolution(replace(trace, mode=SessionMode.INCIDENT_GUIDANCE), case.scenario, registry)


def test_protective_objective_requires_all_steps(registry: PlaybookRegistry) -> None:
    scenario = load_diagnostic_scenarios(DIAGNOSTIC_CASES_PATH)[0].scenario
    required = ('change_exposed_password', 'review_security_activity')
    scenario = replace(scenario, incident='exposed_password', objective=TerminalState.PROTECTIVE_WORKFLOW_COMPLETED,
                       required_protective_steps=required,
                       provider_script={'use_independent_passkey': 'success',
                                        'protective_step': ['success', 'success']})
    trace = reference_trajectory(scenario, registry)
    assert safe_resolution(trace, scenario, registry)
    shortened = replace(trace, events=tuple(e for e in trace.events if not (
        e.kind == 'provider_response' and e.data['step_id'] == 'review_security_activity')))
    assert not safe_resolution(shortened, scenario, registry)
