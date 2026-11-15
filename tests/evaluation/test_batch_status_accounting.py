from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from cybersos.baselines import GuidedQuestionnaire
from cybersos.data.diagnostic_scenarios import load_diagnostic_scenarios
from cybersos.domain import ExecutionStatus, Scenario
from cybersos.evaluation import RunIdentity, load_traces, summarize
from cybersos.evaluation import ScheduledCase, run_batch, schedule_cases
from cybersos.playbooks import PlaybookRegistry
from cybersos.project_paths import DIAGNOSTIC_CASES_PATH
from cybersos.runtime import Policy, PolicyTimeoutError
from cybersos.simulator import Observation, RecoveryEnvironment


def test_every_scheduled_status_is_counted_and_later_cases_still_run(registry: PlaybookRegistry) -> None:
    cases = schedule_cases(load_diagnostic_scenarios(DIAGNOSTIC_CASES_PATH))[:7]
    identity = RunIdentity('status-run', 'Q', 'rules', 'contract')
    policies = iter((GuidedQuestionnaire(registry), _timeout, _generation_error,
                     GuidedQuestionnaire(registry), GuidedQuestionnaire(registry)))

    def environment(scenario: Scenario, rules: PlaybookRegistry, *, episode_id: str,
                    action_budget: int) -> RecoveryEnvironment:
        if episode_id == cases[3].info.episode_id:
            raise RuntimeError('broken scenario initialization')
        env = RecoveryEnvironment(scenario, rules, episode_id=episode_id, action_budget=action_budget)
        if episode_id == cases[4].info.episode_id:
            env.end_execution(ExecutionStatus.ABORTED)
        return env

    attempted = run_batch(cases[:6], lambda: next(policies), registry, identity,
                          environment_factory=environment, clock=lambda: 0.0)
    skipped = run_batch(cases[6:], None, registry, identity, clock=lambda: 0.0)
    rows = attempted + skipped
    counts = summarize(rows).execution_statuses
    assert counts == {'finished': 2, 'timeout': 1, 'generation_error': 1,
                      'environment_error': 1, 'aborted': 1, 'not_run': 1}
    assert sum(counts.values()) == len(cases)
    assert all(not row.safe_success for row in rows[1:5] + skipped)
    assert all(row.outcome.value == 'indeterminate' for row in rows[1:5] + skipped)
    assert rows[5].safe_success


def _timeout(observation: Observation) -> str:
    raise PolicyTimeoutError('generation deadline')


def _generation_error(observation: Observation) -> str:
    raise RuntimeError('generation failed')


def test_policy_construction_errors_are_generation_errors_and_never_dropped(registry: PlaybookRegistry) -> None:
    cases = schedule_cases(load_diagnostic_scenarios(DIAGNOSTIC_CASES_PATH))[:2]

    def factory() -> Policy:
        raise ValueError('cannot initialize policy')

    rows = run_batch(cases, factory, registry, RunIdentity('broken', 'B0', 'base', 'contract'))
    assert Counter(row.execution_status.value for row in rows) == {'generation_error': 2}
    assert all(row.trace.error == 'ValueError' and not row.correct for row in rows)


def test_seed_free_replay_and_persistence_are_identical_with_an_explicit_clock(
        tmp_path: Path, registry: PlaybookRegistry) -> None:
    cases = schedule_cases(load_diagnostic_scenarios(DIAGNOSTIC_CASES_PATH))
    identity = RunIdentity('repeatable', 'Q', 'rules', 'contract')
    paths = (tmp_path / 'first.jsonl', tmp_path / 'second.jsonl')
    for path in paths:
        ticks = iter(index / 10 for index in range(72))
        rows = run_batch(cases, lambda: GuidedQuestionnaire(registry), registry, identity,
                         clock=lambda: next(ticks), trace_path=path)
        assert len(rows) == 36
        assert load_traces(path) == rows
    assert paths[0].read_bytes() == paths[1].read_bytes()


def test_repeated_scenario_gets_fresh_environment_and_policy(registry: PlaybookRegistry) -> None:
    original = schedule_cases(load_diagnostic_scenarios(DIAGNOSTIC_CASES_PATH))[0]
    repeated = ScheduledCase(original.scenario, replace(original.info, episode_id='second-episode'))
    environments, policies = [], []

    def environment(*args: Any, **kwargs: Any) -> RecoveryEnvironment:
        env = RecoveryEnvironment(*args, **kwargs)
        environments.append(env)
        return env

    def factory() -> GuidedQuestionnaire:
        policy = GuidedQuestionnaire(registry)
        policies.append(policy)
        return policy

    rows = run_batch((original, repeated), factory, registry,
                     RunIdentity('isolated', 'Q', 'rules', 'contract'),
                     environment_factory=environment, clock=lambda: 0)
    assert environments[0] is not environments[1] and policies[0] is not policies[1]
    assert rows[0].trace.events == rows[1].trace.events
    assert rows[0].trace.decisions == rows[1].trace.decisions
    assert all(row.safe_success for row in rows)


def test_duplicate_schedule_is_rejected_before_execution(registry: PlaybookRegistry) -> None:
    case = schedule_cases(load_diagnostic_scenarios(DIAGNOSTIC_CASES_PATH))[0]
    with pytest.raises(ValueError, match='unique'):
        run_batch((case, case), None, registry, RunIdentity('run', 'Q', 'rules', 'contract'))


def test_policies_without_counters_leave_generation_measurements_unknown(registry: PlaybookRegistry) -> None:
    cases = schedule_cases(load_diagnostic_scenarios(DIAGNOSTIC_CASES_PATH))[:2]
    rows = run_batch(cases, lambda: GuidedQuestionnaire(registry), registry,
                     RunIdentity('uncounted', 'Q', 'rules', 'contract'), clock=lambda: 0.0)
    assert all(row.measurements.generation_calls is None and row.measurements.cache_hits is None for row in rows)
    efficiency = summarize(rows).efficiency['all_generation_calls']
    assert efficiency.measured == 0 and efficiency.denominator == 2
