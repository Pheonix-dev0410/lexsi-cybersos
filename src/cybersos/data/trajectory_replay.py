from dataclasses import dataclass

from cybersos.data.decision_rows import Record
from cybersos.domain import Scenario, TaskOutcome
from cybersos.oracle import safe_resolution
from cybersos.playbooks import PlaybookRegistry
from cybersos.runtime import EpisodeTrace, run_episode
from cybersos.safety import GuardContext
from cybersos.serialization import canonical_json_sha256, to_json_value
from cybersos.simulator import Observation, RecoveryEnvironment


@dataclass(frozen=True)
class ReplayedTrajectory:
    trace: EpisodeTrace
    observations: tuple[Observation, ...]
    contexts: tuple[GuardContext, ...]


def trace_signature(trace: EpisodeTrace) -> str:
    return canonical_json_sha256([
        {'action': decision.raw_proposal, 'allowed': decision.guard_verdict.allowed,
         'result': {'ok': decision.tool_result.ok, 'data': to_json_value(decision.tool_result.data),
                    'error': decision.tool_result.error, 'paused': decision.tool_result.paused}}
        for decision in trace.decisions])


def replay_actions(scenario: Scenario, registry: PlaybookRegistry, actions: list[str], *,
                   episode_id: str) -> ReplayedTrajectory:
    observations: list[Observation] = []
    contexts: list[GuardContext] = []
    environment = RecoveryEnvironment(scenario, registry, episode_id=episode_id)

    def propose(observation: Observation) -> str:
        index = len(observations)
        observations.append(observation)
        contexts.append(environment.guard_context())
        if index >= len(actions):
            raise ValueError('trajectory_exhausted')
        return actions[index]

    trace = run_episode(propose, environment)
    return ReplayedTrajectory(trace, tuple(observations[:len(trace.decisions)]),
                              tuple(contexts[:len(trace.decisions)]))


def require_safe_replay(trace: EpisodeTrace, scenario: Scenario, registry: PlaybookRegistry,
                        actions: list[str]) -> None:
    """Only a fully executed, allowed, objective-meeting safe trajectory may supervise."""
    if (len(trace.decisions) != len(actions) or trace.outcome != TaskOutcome.OBJECTIVE_MET or
            not safe_resolution(trace, scenario, registry)):
        raise ValueError('replay_mismatch')
    if any(not decision.guard_verdict.allowed for decision in trace.decisions):
        raise ValueError('infeasible_action')


def replay_trajectory(record: Record, registry: PlaybookRegistry) -> ReplayedTrajectory:
    scenario = Scenario.from_mapping(record['episode']['scenario'])
    replayed = replay_actions(scenario, registry, record['actions'],
                              episode_id=record['trajectory_id'])
    trace = replayed.trace
    if (trace.terminal_state != record['terminal_state'] or trace.outcome != record['outcome'] or
            trace.execution_status != record['execution_status'] or
            trace_signature(trace) != record['trace_signature']):
        raise ValueError('replay_mismatch')
    require_safe_replay(trace, scenario, registry, record['actions'])
    return replayed
