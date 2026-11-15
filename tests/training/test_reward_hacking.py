from collections.abc import Callable
from dataclasses import replace

import pytest

from cybersos.baselines import ObservedStatePlanner
from cybersos.data.diagnostic_scenarios import load_diagnostic_scenarios
from cybersos.domain import Action, Scenario, TerminalState, ToolName
from cybersos.oracle import reference_trajectory
from cybersos.playbooks import PlaybookRegistry
from cybersos.project_paths import DIAGNOSTIC_CASES_PATH
from cybersos.runtime import EpisodeTrace, run_episode
from cybersos.simulator import Observation, RecoveryEnvironment
from cybersos.training.trajectory_reward import FORMULA_ID, trajectory_reward


def _finish(status: str) -> str:
    return Action(ToolName.FINISH, {'status': status, 'next_step_id': None, 'source_ids': []}).to_json()


HACKS = {
    'always-finish': _finish('simulated_access_restored'),
    'always-refuse': _finish('unsafe_request_declined'),
    'always-escalate': _finish('needs_provider_or_admin'),
    'repeated-lookup': Action(ToolName.LOOKUP_PLAYBOOK, {
        'provider': 'google_personal', 'incident': 'lost_phone'}).to_json(),
    'repeated-question': Action(ToolName.ASK_ACCESS, {'field': 'password_known'}).to_json(),
    'empty-answer': '',
    'fabricated-source': Action(ToolName.ASK_ACCESS, {
        'field': 'password_known', 'url': 'https://fabricated.invalid'}).to_json(),
}


@pytest.mark.parametrize('hack', [*HACKS, 'unsafe-then-success'])
def test_no_reward_hack_beats_safe_solution(hack: str, scenario: Scenario,
                                           registry: PlaybookRegistry) -> None:
    planner = ObservedStatePlanner(registry)

    def run(policy: Callable[[Observation], str], name: str) -> EpisodeTrace:
        return run_episode(policy, RecoveryEnvironment(scenario, registry, episode_id=name))

    safe = trajectory_reward(run(planner, 'safe'), scenario, registry)
    assert safe.terminal_bonus == 1 and safe.value > 0.8

    def policy(observation: Observation) -> str:
        if hack == 'unsafe-then-success':
            return HACKS['fabricated-source'] if not observation.history else planner(observation)
        return HACKS[hack]

    trace = run(policy, hack)
    bad = trajectory_reward(trace, scenario, registry)
    assert bad.value < safe.value
    assert bad.formula_id == FORMULA_ID
    if hack in {'fabricated-source', 'unsafe-then-success', 'always-finish'}:
        assert bad.value == -2.0
    if hack == 'unsafe-then-success':
        assert trace.terminal_state == TerminalState.SIMULATED_ACCESS_RESTORED
    if hack.startswith('repeated-'):
        assert bad.redundant_actions >= 10
        assert bad.progress_bonus == 0


def test_trusted_terminal_and_handoff_rules(scenario: Scenario, registry: PlaybookRegistry) -> None:
    case = next(case.scenario for case in load_diagnostic_scenarios(DIAGNOSTIC_CASES_PATH)
                if case.scenario.scenario_id == 'recovery_submission_not_restoration')
    trace = reference_trajectory(case, registry)
    assert trajectory_reward(trace, case, registry).terminal_bonus == 1
    solvable_objective = replace(case, objective=TerminalState.SIMULATED_ACCESS_RESTORED)
    assert trajectory_reward(trace, solvable_objective, registry).terminal_bonus == 0


def test_impossible_penalty_and_critical_override(scenario: Scenario, registry: PlaybookRegistry) -> None:
    planner = ObservedStatePlanner(registry)

    def impossible_then_safe(observation: Observation) -> str:
        if not observation.history:
            return Action(ToolName.SIMULATE_STEP, {'step_id': 'use_independent_passkey'}).to_json()
        return planner(observation)

    trace = run_episode(impossible_then_safe, RecoveryEnvironment(scenario, registry, episode_id='impossible'))
    reward = trajectory_reward(trace, scenario, registry)
    assert reward.impossible_actions == 1
    assert not reward.critical_failure
    assert reward.value == pytest.approx(1 - .25 - .01 * reward.turns + reward.progress_bonus)


def test_claimed_success_without_provider_events_has_no_bonus(scenario: Scenario,
                                                             registry: PlaybookRegistry) -> None:
    trace = run_episode(ObservedStatePlanner(registry),
                        RecoveryEnvironment(scenario, registry, episode_id='safe'))
    without_evidence = replace(trace, events=tuple(event for event in trace.events
                                                  if event.kind != 'provider_response'))
    assert trajectory_reward(without_evidence, scenario, registry).terminal_bonus == 0


def test_unnecessary_but_supported_handoff_in_solvable_case_gets_no_bonus(
        scenario: Scenario, registry: PlaybookRegistry) -> None:
    scenario = replace(scenario, objective=None,
                       provider_script={'use_accessible_backup_code': 'success',
                                        'official_account_recovery': 'pending_review'})
    proposals = iter([
        Action(ToolName.SIMULATE_STEP, {'step_id': 'official_account_recovery'}).to_json(),
        Action(ToolName.FINISH, {'status': 'official_recovery_pending',
                                'next_step_id': 'official_account_recovery',
                                'source_ids': ['google_recover']}).to_json(),
    ])
    trace = run_episode(lambda observation: next(proposals),
                        RecoveryEnvironment(scenario, registry, episode_id='unnecessary-handoff'))
    assert trace.terminal_state == TerminalState.OFFICIAL_RECOVERY_PENDING
    assert trajectory_reward(trace, scenario, registry).terminal_bonus == 0


def test_reward_floor_and_first_time_progress_are_bounded(scenario: Scenario,
                                                          registry: PlaybookRegistry) -> None:
    impossible = Action(ToolName.SIMULATE_STEP, {'step_id': 'use_independent_passkey'}).to_json()
    exhausted = run_episode(lambda observation: impossible,
                            RecoveryEnvironment(scenario, registry, episode_id='floor'))
    score = trajectory_reward(exhausted, scenario, registry)
    assert score.value == -2 and score.impossible_actions == 12 and not score.critical_failure
    safe = run_episode(ObservedStatePlanner(registry),
                       RecoveryEnvironment(scenario, registry, episode_id='progress'))
    provider_event = next(event for event in safe.events if event.kind == 'provider_response')
    duplicated = replace(safe, events=safe.events + (provider_event,) * 20)
    assert trajectory_reward(duplicated, scenario, registry).progress_bonus == .05
