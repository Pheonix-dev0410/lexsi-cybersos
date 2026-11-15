from dataclasses import replace

import pytest

from cybersos.baselines import GuidedQuestionnaire
from cybersos.domain import AccessField, Availability, FactSource, Incident, ToolName
from cybersos.data.diagnostic_scenarios import DiagnosticCase
from cybersos.playbooks import PlaybookRegistry
from cybersos.runtime import run_episode
from cybersos.safety import parse_action
from cybersos.simulator import RecoveryEnvironment


@pytest.mark.parametrize('incident', list(Incident))
def test_questionnaire_completes_its_ordered_page_before_recommending_a_ready_alternative(
        registry: PlaybookRegistry, cases: tuple[DiagnosticCase, ...], incident: Incident) -> None:
    scenario = next(case.scenario for case in cases if case.scenario.scenario_id == 'paper_backup_saved')
    required_questions = [AccessField.PASSWORD_KNOWN, AccessField.INDEPENDENT_PASSKEY_AVAILABLE,
                          AccessField.BACKUP_CODE_EXISTS, AccessField.BACKUP_CODE_ACCESSIBLE_NOW]
    enrollment = {AccessField.ENROLLED_SECURITY_KEY_AVAILABLE: True,
                  AccessField.ENROLLED_SECURITY_KEY_EXISTS: True,
                  AccessField.INDEPENDENT_PASSKEY_EXISTS: True}
    access = dict(scenario.access) | enrollment
    intake = {field: value for field, value in scenario.initial_facts.items()
              if field not in required_questions} | enrollment
    scenario = replace(scenario, incident=incident, access=access, initial_facts=intake)
    environment = RecoveryEnvironment(scenario, registry, episode_id='fixed-order')
    trace = run_episode(GuidedQuestionnaire(registry), environment)
    actions = [decision.action for decision in trace.decisions if decision.action]
    assert [action.parameters['field'] for action in actions if action.tool_name == ToolName.ASK_ACCESS] == [
        field.value for field in required_questions]
    assert actions[-2].tool_name == ToolName.SIMULATE_STEP
    assert actions[-2].parameters['step_id'] == 'use_accessible_backup_code'
    assert all(decision.guard_verdict.allowed for decision in trace.decisions)


@pytest.mark.parametrize('answer', [Availability.TRUE, Availability.FALSE, Availability.UNKNOWN])
def test_branching_answers_preserve_unknown_and_skip_only_a_negative_dependency(
        registry: PlaybookRegistry, cases: tuple[DiagnosticCase, ...], answer: Availability) -> None:
    scenario = next(case.scenario for case in cases
                    if case.scenario.scenario_id == 'recovery_submission_not_restoration')
    missing = {AccessField.BACKUP_CODE_EXISTS, AccessField.BACKUP_CODE_ACCESSIBLE_NOW}
    scenario = replace(scenario,
                       access=dict(scenario.access) | {AccessField.BACKUP_CODE_EXISTS: answer},
                       initial_facts={field: value for field, value in scenario.initial_facts.items()
                                      if field not in missing})
    environment = RecoveryEnvironment(scenario, registry, episode_id='branch-answer')
    trace = run_episode(GuidedQuestionnaire(registry), environment)
    asked = [decision.action.parameters['field'] for decision in trace.decisions
             if decision.action and decision.action.tool_name == ToolName.ASK_ACCESS]
    assert asked == ([AccessField.BACKUP_CODE_EXISTS.value] if answer == Availability.FALSE else
                     [AccessField.BACKUP_CODE_EXISTS.value, AccessField.BACKUP_CODE_ACCESSIBLE_NOW.value])
    assert environment.observation().observed_facts.value(AccessField.BACKUP_CODE_EXISTS) == answer
    assert trace.terminal_state == scenario.objective
    assert all(decision.guard_verdict.allowed for decision in trace.decisions)


def test_a_corrected_answer_reopens_a_previously_skipped_page(
        registry: PlaybookRegistry, cases: tuple[DiagnosticCase, ...]) -> None:
    scenario = next(case.scenario for case in cases
                    if case.scenario.scenario_id == 'recovery_submission_not_restoration')
    scenario = replace(scenario, initial_facts={
        field: value for field, value in scenario.initial_facts.items()
        if field not in {AccessField.BACKUP_CODE_ACCESSIBLE_NOW, AccessField.ACTIVE_SESSION_ELSEWHERE}})
    environment = RecoveryEnvironment(scenario, registry, episode_id='reopened-page')
    questionnaire = GuidedQuestionnaire(registry)
    before = parse_action(questionnaire(environment.observation())).action
    assert before is not None and before.parameters['field'] == AccessField.ACTIVE_SESSION_ELSEWHERE
    environment.update_fact(AccessField.BACKUP_CODE_EXISTS, True,
                            source=FactSource.USER_REPORTED, correction=True)
    after = parse_action(questionnaire(environment.observation())).action
    assert after is not None and after.tool_name == ToolName.ASK_ACCESS
    assert after.parameters['field'] == AccessField.BACKUP_CODE_ACCESSIBLE_NOW
