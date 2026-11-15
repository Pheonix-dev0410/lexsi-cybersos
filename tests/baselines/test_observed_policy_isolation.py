from collections.abc import Callable
from dataclasses import replace

import pytest

from cybersos.baselines import GuidedQuestionnaire, ObservedStatePlanner
from cybersos.data.diagnostic_scenarios import DiagnosticCase
from cybersos.domain import AccessField, Scenario, ToolName
from cybersos.playbooks import PlaybookRegistry
from cybersos.runtime import EpisodeTrace, Policy
from cybersos.safety import parse_action
from cybersos.simulator import RecoveryEnvironment


@pytest.mark.parametrize('policy_type', [GuidedQuestionnaire, ObservedStatePlanner])
def test_policy_cannot_consult_hidden_answers_or_scripts(
        registry: PlaybookRegistry, cases: tuple[DiagnosticCase, ...], monkeypatch: pytest.MonkeyPatch,
        policy_type: type[GuidedQuestionnaire] | type[ObservedStatePlanner]) -> None:
    scenario = cases[0].scenario
    other = replace(scenario, scenario_id='different-hidden-root',
                    access={AccessField.INDEPENDENT_PASSKEY_AVAILABLE: False},
                    provider_script={'use_independent_passkey': 'denial'}, objective=None)
    observations = [RecoveryEnvironment(s, registry, episode_id='isolated').observation()
                    for s in (scenario, other)]

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError('A policy read hidden state')

    monkeypatch.setattr(Scenario, 'hidden_answer', forbidden)
    monkeypatch.setattr(RecoveryEnvironment, 'trusted_snapshot', forbidden)
    assert observations[0] == observations[1]
    assert policy_type(registry)(observations[0]) == policy_type(registry)(observations[1])


@pytest.mark.parametrize('policy_type', [GuidedQuestionnaire, ObservedStatePlanner])
def test_corrections_invalidate_the_old_route(
        registry: PlaybookRegistry, cases: tuple[DiagnosticCase, ...],
        run_case: Callable[[DiagnosticCase, Policy], EpisodeTrace],
        policy_type: type[GuidedQuestionnaire] | type[ObservedStatePlanner]) -> None:
    corrected = [case for case in cases if case.scenario.corrections]
    assert corrected
    for case in corrected:
        trace = run_case(case, policy_type(registry))
        assert any(e.kind == 'fact_recorded' and e.data['correction'] for e in trace.events)
        assert [d.action.parameters['step_id'] for d in trace.decisions
                if d.action and d.action.tool_name == ToolName.SIMULATE_STEP] == ['official_account_recovery']


def test_unknown_factor_is_asked_without_assuming_success(
        registry: PlaybookRegistry, cases: tuple[DiagnosticCase, ...]) -> None:
    case = next(c for c in cases if c.scenario.scenario_id == 'backup_location_uncertain')
    env = RecoveryEnvironment(case.scenario, registry, episode_id='unknown')
    parsed = parse_action(ObservedStatePlanner(registry)(env.observation()))
    assert parsed.action is not None
    assert parsed.action.tool_name == ToolName.ASK_ACCESS
    assert parsed.action.parameters['field'] == 'backup_code_accessible_now'
