from dataclasses import replace

import pytest

from cybersos.baselines import GuidedQuestionnaire, ObservedStatePlanner
from cybersos.data.diagnostic_scenarios import DiagnosticCase
from cybersos.domain import AccessField, ToolName
from cybersos.oracle import safe_resolution
from cybersos.playbooks import PlaybookRegistry
from cybersos.runtime import run_episode
from cybersos.simulator import RecoveryEnvironment


@pytest.mark.parametrize(('scenario_id', 'expected_counts'), [
    ('codes_inside_locked_drive', [1, 0]), ('independent_laptop_passkey', [2, 1])])
def test_questionnaire_and_planner_resolve_the_same_objective_with_measurable_question_burden(
        registry: PlaybookRegistry, cases: tuple[DiagnosticCase, ...], scenario_id: str,
        expected_counts: list[int]) -> None:
    scenario = next(case.scenario for case in cases if case.scenario.scenario_id == scenario_id)
    scenario = replace(scenario, initial_facts={
        field: value for field, value in scenario.initial_facts.items()
        if field not in {AccessField.PASSWORD_KNOWN, AccessField.INDEPENDENT_PASSKEY_AVAILABLE}})
    question_counts: list[int] = []
    for policy_type in (GuidedQuestionnaire, ObservedStatePlanner):
        trace = run_episode(policy_type(registry), RecoveryEnvironment(
            scenario, registry, episode_id=policy_type.__name__))
        assert trace.terminal_state == scenario.objective
        assert safe_resolution(trace, scenario, registry)
        question_counts.append(sum(decision.action is not None and
                                   decision.action.tool_name == ToolName.ASK_ACCESS
                                   for decision in trace.decisions))
        assert all(decision.action is None or
                   decision.action.parameters.get('step_id') != 'use_accessible_backup_code'
                   for decision in trace.decisions)
    assert question_counts == expected_counts

