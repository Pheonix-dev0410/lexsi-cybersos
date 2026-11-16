from dataclasses import dataclass
from pathlib import Path

from cybersos.data.decision_rows import Record, Row, decision_row, row_hash
from cybersos.data.privacy_scanning import privacy_errors
from cybersos.data.scenario_records import ScenarioEpisode, Split
from cybersos.data.source_evidence import source_evidence
from cybersos.data.split_artifacts import episode_mapping
from cybersos.baselines import ObservedStatePlanner
from cybersos.data.trajectory_replay import (
    ReplayedTrajectory, replay_actions, require_safe_replay, trace_signature,
)
from cybersos.domain import Action, Scenario, ToolName
from cybersos.oracle import reference_trajectory
from cybersos.playbooks import PlaybookRegistry
from cybersos.runtime import run_episode
from cybersos.simulator import RecoveryEnvironment
from cybersos.serialization import write_json, write_jsonl


@dataclass(frozen=True)
class DecisionExamples:
    rows: tuple[Row, ...]
    provenance: dict[str, list[Record]]
    trajectories: tuple[Record, ...]
    exclusions: tuple[Record, ...]


def build_decision_examples(episodes: tuple[ScenarioEpisode, ...],
                            registry: PlaybookRegistry) -> DecisionExamples:
    rows: list[Row] = []
    provenance: dict[str, list[Record]] = {}
    trajectories: list[Record] = []
    exclusions: list[Record] = []
    for episode in episodes:
        if episode.split != Split.TRAIN:
            raise ValueError('Only training roots may become supervised examples')
        scenario = episode.scenario
        identifier = f'train:{scenario.scenario_id}'
        try:
            teacher, actions, replayed = _verified_teacher_trajectory(scenario, registry, identifier)
        except ValueError as error:
            exclusions.append({'scenario_id': scenario.scenario_id, 'root_id': episode.root.root_id,
                               'reason': str(error)})
            continue
        trace = replayed.trace
        episode_rows = [decision_row(observation, decision.raw_proposal)
                        for observation, decision in zip(replayed.observations, trace.decisions)]
        if any(privacy_errors(row) for row in episode_rows):
            exclusions.append({'scenario_id': scenario.scenario_id, 'root_id': episode.root.root_id,
                               'reason': 'sensitive_training_input'})
            continue
        trajectory = {'trajectory_id': identifier, 'teacher': teacher,
                      'episode': episode_mapping(episode),
                      'actions': actions, 'terminal_state': trace.terminal_state,
                      'outcome': trace.outcome, 'execution_status': trace.execution_status,
                      'trace_signature': trace_signature(trace),
                      'evidence': source_evidence(scenario, registry)}
        trajectories.append(trajectory)
        for turn, row in enumerate(episode_rows):
            rows.append(row)
            origin = {'trajectory_id': identifier, 'turn': turn, 'root_id': episode.root.root_id,
                      'root_hash': episode.root.root_hash, 'split': 'train',
                      'paraphrase_id': episode.paraphrase_id, 'pair_id': episode.root.pair_id,
                      'changed_field': episode.root.changed_field,
                      'evidence': trajectory['evidence']}
            provenance.setdefault(row_hash(row), []).append(origin)
    return DecisionExamples(tuple(rows), provenance, tuple(trajectories), tuple(exclusions))


def _verified_teacher_trajectory(scenario: Scenario, registry: PlaybookRegistry,
                                 identifier: str) -> tuple[str, list[str], ReplayedTrajectory]:
    """Prefer the observed-state planner R; fall back to the full-state route.

    The policy imitates what it can see, so the teacher must decide from observed facts too.
    The oracle picks which factor to ask about from hidden state, and SFT on it collapsed to
    the most common route; it only covers episodes R cannot finish. Trajectories run exactly
    as the R baseline does, without a lookup: R rules out every factor before the fallback and
    needs the whole 12-action budget, so a lookup would exhaust it.
    """
    failures: list[str] = []
    for teacher, propose in _TEACHERS:
        try:
            actions = propose(scenario, registry)
            replayed = replay_actions(scenario, registry, actions, episode_id=identifier)
            require_safe_replay(replayed.trace, scenario, registry, actions)
            return teacher, actions, replayed
        except ValueError as error:
            failures.append(f'{teacher}: {error}')
    raise ValueError('; '.join(failures))


def _oracle_route(scenario: Scenario, registry: PlaybookRegistry) -> list[str]:
    return [turn.raw_proposal for turn in reference_trajectory(scenario, registry).decisions]


def _observed_state_planner(scenario: Scenario, registry: PlaybookRegistry) -> list[str]:
    planner = ObservedStatePlanner(registry, scenario.required_protective_steps)
    environment = RecoveryEnvironment(scenario, registry, episode_id=f'teacher:{scenario.scenario_id}')
    return [turn.raw_proposal for turn in run_episode(planner, environment).decisions]


TEACHER_GENERATOR = ('deterministic teachers (observed-state planner R, else oracle route); '
                     'simulator replay; no LLM teacher')
_TEACHERS = (('observed_state_planner', _observed_state_planner), ('oracle_route', _oracle_route))


def save_decision_examples(examples: DecisionExamples, directory: str | Path, *, seed: int,
                           generator: str = TEACHER_GENERATOR) -> Record:
    destination = Path(directory)
    write_jsonl(destination / 'train_candidates.jsonl', examples.rows)
    write_json(destination / 'provenance.json', examples.provenance)
    write_jsonl(destination / 'trajectories.jsonl', examples.trajectories)
    write_jsonl(destination / 'excluded_episodes.jsonl', examples.exclusions)
    manifest = {'seed': seed, 'candidate_rows': len(examples.rows),
                'successful_trajectories': len(examples.trajectories),
                'excluded_episodes': len(examples.exclusions),
                'generator': generator,
                'provenance_visibility': 'evaluator_only'}
    write_json(destination / 'manifest.json', manifest)
    if not examples.rows:
        raise ValueError('No successful supervised examples; see excluded_episodes.jsonl')
    return manifest
