from cybersos.data.decision_rows import Record, Row, decision_row, require_alpaca_row, row_hash
from cybersos.data.privacy_scanning import privacy_errors
from cybersos.data.scenario_fingerprints import root_hash
from cybersos.data.scenario_loading import episode_from_mapping
from cybersos.data.source_evidence import evidence_errors
from cybersos.data.trajectory_replay import ReplayedTrajectory, replay_trajectory
from cybersos.playbooks import PlaybookRegistry
from cybersos.safety import guard_action, parse_action
from cybersos.safety.action_schema import schema_error
from cybersos.serialization import canonical_json_sha256


class DecisionGates:
    def __init__(self, trajectories: list[Record], registry: PlaybookRegistry, *,
                 training_episodes: list[Record] | None = None) -> None:
        self.training_episodes = ({row['scenario']['scenario_id']: row for row in training_episodes}
                                  if training_episodes is not None else None)
        self.registry = registry
        self.trajectories = {record['trajectory_id']: record for record in trajectories}
        if len(self.trajectories) != len(trajectories):
            raise ValueError('duplicate_trajectory_id')
        self._replays: dict[str, ReplayedTrajectory | str] = {}

    def replay(self, identifier: str) -> ReplayedTrajectory:
        if identifier not in self._replays:
            try:
                self._replays[identifier] = replay_trajectory(self.trajectories[identifier], self.registry)
            except (KeyError, ValueError, TypeError) as error:
                self._replays[identifier] = str(error)
        result = self._replays[identifier]
        if isinstance(result, str):
            raise ValueError(f'replay_mismatch:{result}')
        return result

    def check(self, row: Row, origins: list[Record]) -> tuple[str, ...]:
        errors: list[str] = []
        try:
            require_alpaca_row(row)
        except ValueError:
            return ('invalid_schema',)
        errors.extend(privacy_errors(row))
        if not row['output'].strip():
            errors.append('empty_completion')
        parsed = parse_action(row['output'])
        if parsed.action is None or schema_error(parsed.action):
            errors.append('invalid_action')
        if not origins:
            errors.append('missing_provenance')
        for origin in origins:
            try:
                errors.extend(self._check_origin(row, origin))
            except (ValueError, KeyError, TypeError, IndexError, AttributeError) as error:
                errors.append(str(error))
        return tuple(sorted(set(errors)))

    def _check_origin(self, row: Row, origin: Record) -> list[str]:
        record = self.trajectories[origin['trajectory_id']]
        episode = episode_from_mapping(record['episode'])
        if self.training_episodes is not None:
            expected = self.training_episodes.get(episode.scenario.scenario_id)
            if expected is None or canonical_json_sha256(expected) != canonical_json_sha256(record['episode']):
                raise ValueError('nontraining_or_changed_scenario')
        if (origin['split'] != 'train' or episode.split != 'train' or
                origin['root_id'] != episode.root.root_id or
                origin['root_hash'] != root_hash(episode.scenario, episode.root.template_id) or
                origin['paraphrase_id'] != episode.paraphrase_id or
                origin['pair_id'] != episode.root.pair_id or
                origin['changed_field'] != episode.root.changed_field):
            raise ValueError('root_provenance_mismatch')
        replayed = self.replay(origin['trajectory_id'])
        turn = origin['turn']
        if type(turn) is not int or not 0 <= turn < len(replayed.trace.decisions):
            raise ValueError('invalid_turn')
        observation = replayed.observations[turn]
        decision = replayed.trace.decisions[turn]
        errors = []
        if decision_row(observation, decision.raw_proposal) != row:
            errors.append('observation_or_action_mismatch')
        parsed = parse_action(row['output'])
        if parsed.action is not None:
            if not guard_action(parsed.action, replayed.contexts[turn],
                                raw_text=row['output']).allowed:
                errors.append('infeasible_action')
            errors.extend(evidence_errors(origin['evidence'], parsed.action,
                                          episode.scenario, self.registry))
        if record['evidence'] != origin['evidence']:
            errors.append('source_provenance_mismatch')
        return errors


def check_export_count(accepted_count: int, exported_rows: list[Row]) -> None:
    if accepted_count != len(exported_rows):
        raise ValueError('accepted_export_count_mismatch')
    if len({row_hash(row) for row in exported_rows}) != len(exported_rows):
        raise ValueError('duplicate_export_rows')


def check_counterfactual_preservation(before: dict[str, list[Record]],
                                      after: dict[str, list[Record]]) -> None:
    def coverage(sidecar: dict[str, list[Record]]) -> set[tuple[str, str, str]]:
        return {(origin['pair_id'], origin['root_hash'], digest)
                for digest, origins in sidecar.items() for origin in origins if origin.get('pair_id')}

    if not coverage(before) <= coverage(after):
        raise ValueError('collapsed_counterfactual_pair')
