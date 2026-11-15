from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from time import monotonic

from cybersos.data.diagnostic_scenarios import DiagnosticCase
from cybersos.domain import ExecutionStatus, Scenario, SessionMode, TaskOutcome, TerminalState
from cybersos.evaluation.trace_records import CaseInfo, Measurements, RunIdentity, TraceRecord, record_episode
from cybersos.evaluation.trace_serialization import write_traces
from cybersos.playbooks import PlaybookRegistry
from cybersos.runtime import EpisodeRunner, EpisodeTrace, Policy, PolicyTimeoutError
from cybersos.simulator import RecoveryEnvironment


@dataclass(frozen=True)
class ScheduledCase:
    scenario: Scenario
    info: CaseInfo


ELIGIBLE_TERMINALS = frozenset({TerminalState.SIMULATED_ACCESS_RESTORED, TerminalState.PROTECTIVE_WORKFLOW_COMPLETED})


def schedule_scenario(scenario: Scenario, root_id: str, *, episode_id: str | None = None,
                      pair_id: str | None = None, slices: tuple[str, ...] = ()) -> ScheduledCase:
    """Derive evaluator-owned labels and scripted revisions from the scenario; none reach the policy."""
    objective = scenario.objective
    return ScheduledCase(scenario, CaseInfo(
        scenario.scenario_id, episode_id or scenario.scenario_id, root_id, objective,
        eligible=objective in ELIGIBLE_TERMINALS,
        boundary=objective is not None and objective not in ELIGIBLE_TERMINALS,
        corrections=scenario.corrections, tool_failures=scenario.temporary_tool_failures,
        pair_id=pair_id, slices=slices, opening_message=scenario.opening_message))


def schedule_cases(cases: Sequence[DiagnosticCase]) -> tuple[ScheduledCase, ...]:
    return tuple(schedule_scenario(
        case.scenario, case.root.root_id, pair_id=case.root.pair_id,
        slices=tuple(dict.fromkeys(filter(None, (case.family, case.split, *(
            tag for tag in case.root.tags if tag != 'diagnostic' or case.family or case.split == 'diagnostic'))))))
        for case in cases)


def run_batch(cases: Sequence[ScheduledCase], policy_factory: Callable[[], Policy] | None,
              registry: PlaybookRegistry, identity: RunIdentity, *, action_budget: int = 12,
              clock: Callable[[], float] = monotonic,
              environment_factory: Callable[..., RecoveryEnvironment] = RecoveryEnvironment,
              trace_path: str | Path | None = None) -> tuple[TraceRecord, ...]:
    """Retain every scheduled case, including skipped policies and infrastructure failures.

    Factories receive no hidden scenario data. Only the environment receives the
    scenario; each case gets a new environment and a fresh policy wrapper.
    """
    if not cases or len({case.info.episode_id for case in cases}) != len(cases):
        raise ValueError('A batch needs nonempty, unique scheduled episode IDs')
    if not 1 <= action_budget <= 12:
        raise ValueError('Action budget must be between 1 and 12')
    if any(case.scenario.scenario_id != case.info.scenario_id for case in cases):
        raise ValueError('Scheduled case identity differs from scenario')
    rows = tuple(TraceRecord(identity, case.info) if policy_factory is None else
                 _run_case(case, policy_factory, registry, identity, action_budget, clock, environment_factory)
                 for case in cases)
    if trace_path is not None:
        write_traces(trace_path, rows)
    return rows


def _run_case(case: ScheduledCase, policy_factory: Callable[[], Policy], registry: PlaybookRegistry,
              identity: RunIdentity, action_budget: int, clock: Callable[[], float],
              environment_factory: Callable[..., RecoveryEnvironment]) -> TraceRecord:
    started = clock()
    env, runner, policy = None, None, None
    before: dict[str, int] = {}
    try:
        env = environment_factory(case.scenario, registry, episode_id=case.info.episode_id,
                                  action_budget=action_budget)
        runner = EpisodeRunner(env)
        try:
            policy = policy_factory()
        except Exception as error:
            env.end_execution(ExecutionStatus.TIMEOUT if isinstance(error, PolicyTimeoutError)
                              else ExecutionStatus.GENERATION_ERROR)
            raise
        before = _counters(policy)
        trace = runner.run(policy)
    except Exception as error:
        trace = _failed_trace(case, env, runner, error)
    after = _counters(policy) if policy is not None else {}
    measurements = Measurements(
        latency_seconds=clock() - started,
        input_tokens=_delta(before, after, 'input_tokens'),
        output_tokens=(None if _delta(before, after, 'unmeasured_output_calls') else
                       _delta(before, after, 'output_tokens')),
        generation_calls=_delta(before, after, 'generation_calls'),
        cache_hits=_delta(before, after, 'cache_hits'))
    return record_episode(identity, case.info, trace, env.trusted_snapshot() if env is not None else None,
                          measurements=measurements)


def _failed_trace(case: ScheduledCase, env: RecoveryEnvironment | None, runner: EpisodeRunner | None,
                  error: Exception) -> EpisodeTrace:
    if env is None or runner is None:
        return EpisodeTrace(case.info.episode_id, case.info.scenario_id, SessionMode.BENCHMARK, (), (),
                            TerminalState.ENVIRONMENT_ERROR, ExecutionStatus.ENVIRONMENT_ERROR,
                            TaskOutcome.INDETERMINATE, error=type(error).__name__)
    if not env.done:
        env.end_execution(ExecutionStatus.ENVIRONMENT_ERROR)
    return replace(runner.trace(), error=type(error).__name__)


def _counters(policy: Policy) -> dict[str, int]:
    return dict(getattr(policy, 'counters', {}))


def _delta(before: dict[str, int], after: dict[str, int], key: str) -> int | None:
    """Policies without counters report None, which stays unknown rather than zero."""
    return after[key] - before.get(key, 0) if key in after else None
