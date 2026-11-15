from dataclasses import replace
from typing import Callable

import pytest

from cybersos.baselines import ObservedStatePlanner
from cybersos.data.diagnostic_scenarios import load_diagnostic_scenarios
from cybersos.domain import Action, TerminalState, ToolName
from cybersos.evaluation import RunIdentity, ScheduledCase, TraceRecord, run_batch, schedule_cases, summarize
from cybersos.playbooks import PlaybookRegistry
from cybersos.project_paths import DIAGNOSTIC_CASES_PATH
from cybersos.simulator import Observation

IDENTITY = RunIdentity('revision', 'R', 'rules', 'contract')


@pytest.fixture(scope='module')
def diagnostic_cases() -> dict[str, ScheduledCase]:
    return {case.info.scenario_id: case for case in schedule_cases(load_diagnostic_scenarios(DIAGNOSTIC_CASES_PATH))}


def _run(case: ScheduledCase, policy: Callable[[Observation], str], registry: PlaybookRegistry) -> TraceRecord:
    return run_batch((case,), lambda: policy, registry, IDENTITY, clock=lambda: 0.0)[0]


def test_corrections_are_counted_from_user_correction_events_only(
        diagnostic_cases: dict[str, ScheduledCase], registry: PlaybookRegistry) -> None:
    planner = ObservedStatePlanner(registry)
    corrected = _run(diagnostic_cases['backup_access_corrected'], planner, registry)
    provider_denial = _run(diagnostic_cases['trusted_session_denied'], planner, registry)
    assert any(e.kind == 'fact_recorded' and e.data.get('correction') for e in provider_denial.trace.events)
    assert 'correction' not in summarize([provider_denial]).diagnostic_flags
    assert summarize([corrected]).diagnostic_flags['correction'] == 1


def test_handled_correction_and_retried_tool_failure_count_as_revision_handling(
        diagnostic_cases: dict[str, ScheduledCase], registry: PlaybookRegistry) -> None:
    planner = ObservedStatePlanner(registry)
    for name in ('backup_access_corrected', 'phone_temporary_failure_retry'):
        rate = summarize([_run(diagnostic_cases[name], planner, registry)]).rates['revision_handling']
        assert (rate.numerator, rate.denominator, rate.unknown) == (1, 1, 0)


def test_impossible_step_after_a_correction_is_not_revision_handling(
        diagnostic_cases: dict[str, ScheduledCase], registry: PlaybookRegistry) -> None:
    planner = ObservedStatePlanner(registry)
    stale = Action(ToolName.SIMULATE_STEP, {'step_id': 'use_accessible_backup_code'}).to_json()
    proposed_stale = []

    def ignores_correction(observation: Observation) -> str:
        if any(fact.correction for fact in observation.facts) and not proposed_stale:
            proposed_stale.append(stale)
            return stale
        return planner(observation)

    summary = summarize([_run(diagnostic_cases['backup_access_corrected'], ignores_correction, registry)])
    for name in ('revision_handling', 'corrections_handled'):
        rate = summary.rates[name]
        assert (rate.numerator, rate.denominator, rate.unknown) == (0, 1, 0)


def test_revision_whose_scripted_event_never_fired_is_untested(
        diagnostic_cases: dict[str, ScheduledCase], registry: PlaybookRegistry) -> None:
    finish = Action(ToolName.FINISH, {'status': 'official_recovery_pending', 'next_step_id': None,
                                      'source_ids': []}).to_json()
    rate = summarize([_run(diagnostic_cases['backup_access_corrected'], lambda observation: finish,
                           registry)]).rates['revision_handling']
    assert (rate.numerator, rate.denominator, rate.unknown) == (0, 1, 1)
    assert rate.render() == 'unknown (1 cases)'


def test_refusal_or_handoff_on_a_solvable_case_is_benign_over_refusal(
        episode_record: Callable[..., TraceRecord]) -> None:
    solved = episode_record(episode_id='solved')
    refused = episode_record(episode_id='refused')
    refused = replace(refused, trace=replace(refused.trace, terminal_state=TerminalState.NO_SUPPORTED_PATH_KNOWN))
    unfinished = episode_record(episode_id='unfinished')
    unfinished = replace(unfinished, case=replace(unfinished.case, episode_id='unrun'), trace=None,
                         final_state=None, adjudication=replace(unfinished.adjudication, recommendation_support=()))
    rate = summarize([solved, refused, unfinished]).rates['benign_over_refusal']
    assert (rate.numerator, rate.denominator, rate.unknown) == (1, 3, 1)
