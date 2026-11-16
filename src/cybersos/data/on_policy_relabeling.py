from collections.abc import Callable

from cybersos.baselines import ObservedStatePlanner
from cybersos.data.decision_examples import DecisionExamples
from cybersos.data.decision_rows import Record, Row, decision_row, row_hash
from cybersos.data.privacy_scanning import privacy_errors
from cybersos.data.scenario_records import ScenarioEpisode, Split
from cybersos.data.source_evidence import source_evidence
from cybersos.data.split_artifacts import episode_mapping
from cybersos.data.trajectory_replay import replay_actions, require_teacher_relabel, trace_signature
from cybersos.playbooks import PlaybookRegistry
from cybersos.runtime import run_episode
from cybersos.simulator import Observation, RecoveryEnvironment


RELABEL_TEACHER = 'observed_state_planner_relabel'


def collect_student_actions(policy: Callable[[Observation], str], episodes: tuple[ScenarioEpisode, ...],
                            registry: PlaybookRegistry, *, sample: int = 0) -> list[Record]:
    """Run the student on training scenarios; only its raw proposals are kept for relabeling."""
    records = []
    for episode in episodes:
        if episode.split != Split.TRAIN:
            raise ValueError('Only training scenarios may be relabeled')
        scenario = episode.scenario
        trace = run_episode(policy, RecoveryEnvironment(
            scenario, registry, episode_id=f'student:{scenario.scenario_id}:{sample}'))
        records.append({'scenario_id': scenario.scenario_id, 'sample': sample,
                        'actions': [decision.raw_proposal for decision in trace.decisions],
                        'terminal_state': trace.terminal_state, 'outcome': trace.outcome})
    return records


def relabel_student_actions(episodes: tuple[ScenarioEpisode, ...], student: list[Record],
                            registry: PlaybookRegistry) -> DecisionExamples:
    """DAgger: every state the student reached, including after its own mistakes, gets R's action.

    Only the relabeled turn supervises; the student's earlier actions stay in the history so the
    policy learns to recover from states the teacher's own trajectories never visit.
    """
    rows: list[Row] = []
    provenance: dict[str, list[Record]] = {}
    trajectories: list[Record] = []
    exclusions: list[Record] = []
    by_id = {episode.scenario.scenario_id: episode for episode in episodes}
    for number, record in enumerate(student):
        episode = by_id.get(record['scenario_id'])
        if episode is None or episode.split != Split.TRAIN:
            raise ValueError('Student rollout does not name a training scenario')
        scenario, actions, sample = episode.scenario, record['actions'], record.get('sample', 0)
        visited = replay_actions(scenario, registry, actions,
                                 episode_id=f'student:{scenario.scenario_id}:{sample}')
        planner = ObservedStatePlanner(registry, scenario.required_protective_steps)
        evidence = source_evidence(scenario, registry)
        for turn, observation in enumerate(visited.observations):
            identifier = f'relabel:{scenario.scenario_id}:{number}:{turn}'
            relabeled = [*actions[:turn], planner(observation)]
            replayed = replay_actions(scenario, registry, relabeled, episode_id=identifier)
            try:
                require_teacher_relabel(replayed, scenario, registry, turn)
                row = decision_row(replayed.observations[turn], relabeled[-1])
                if privacy_errors(row):
                    raise ValueError('sensitive_training_input')
            except ValueError as error:
                exclusions.append({'scenario_id': scenario.scenario_id, 'turn': turn, 'reason': str(error)})
                continue
            trace = replayed.trace
            trajectories.append({
                'trajectory_id': identifier, 'teacher': RELABEL_TEACHER, 'relabeled_turn': turn,
                'episode': episode_mapping(episode), 'actions': relabeled,
                'terminal_state': trace.terminal_state, 'outcome': trace.outcome,
                'execution_status': trace.execution_status, 'trace_signature': trace_signature(trace),
                'evidence': evidence})
            rows.append(row)
            provenance.setdefault(row_hash(row), []).append({
                'trajectory_id': identifier, 'turn': turn, 'root_id': episode.root.root_id,
                'root_hash': episode.root.root_hash, 'split': 'train',
                'paraphrase_id': episode.paraphrase_id, 'pair_id': episode.root.pair_id,
                'changed_field': episode.root.changed_field, 'evidence': evidence})
    return DecisionExamples(tuple(rows), provenance, tuple(trajectories), tuple(exclusions))


def merge_examples(first: DecisionExamples, second: DecisionExamples) -> DecisionExamples:
    provenance = {digest: list(origins) for digest, origins in first.provenance.items()}
    for digest, origins in second.provenance.items():
        provenance.setdefault(digest, []).extend(origins)
    return DecisionExamples(first.rows + second.rows, provenance, first.trajectories + second.trajectories,
                            first.exclusions + second.exclusions)
