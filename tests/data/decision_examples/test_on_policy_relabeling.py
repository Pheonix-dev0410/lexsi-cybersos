from cybersos.data.decision_examples import DecisionExamples
from cybersos.data.decision_gates import DecisionGates
from cybersos.data.decision_rows import row_hash
from cybersos.data.on_policy_relabeling import relabel_student_actions
from cybersos.data.scenario_records import ScenarioEpisode
from cybersos.data.split_artifacts import episode_mapping
from cybersos.playbooks import PlaybookRegistry

MISTAKE = 'I think you should just reset everything.'


def _relabeled(examples: DecisionExamples, episodes: tuple[ScenarioEpisode, ...],
               registry: PlaybookRegistry) -> tuple[DecisionExamples, list[str]]:
    episode = episodes[0]
    teacher = next(t for t in examples.trajectories
                   if t['episode']['scenario']['scenario_id'] == episode.scenario.scenario_id)
    student = [MISTAKE, *teacher['actions']]
    records = [{'scenario_id': episode.scenario.scenario_id, 'sample': 0, 'actions': student}]
    return relabel_student_actions((episode,), records, registry), student


def test_states_after_a_student_mistake_get_teacher_labels_that_pass_gates(
        examples: DecisionExamples, training_episodes: tuple[ScenarioEpisode, ...],
        registry: PlaybookRegistry) -> None:
    relabeled, student = _relabeled(examples, training_episodes, registry)
    assert not relabeled.exclusions and len(relabeled.rows) >= 2
    assert all(row['output'] != MISTAKE for row in relabeled.rows)
    assert 'unparsed proposal' in relabeled.rows[1]['instruction']
    gates = DecisionGates(list(relabeled.trajectories), registry,
                          training_episodes=[episode_mapping(e) for e in training_episodes])
    for row in relabeled.rows:
        assert gates.check(row, relabeled.provenance[row_hash(row)]) == ()


def test_student_actions_never_become_targets(
        examples: DecisionExamples, training_episodes: tuple[ScenarioEpisode, ...],
        registry: PlaybookRegistry) -> None:
    relabeled, student = _relabeled(examples, training_episodes, registry)
    record = dict(relabeled.trajectories[1])
    row = relabeled.rows[1]
    gates = DecisionGates([record], registry)
    earlier = [dict(origin, turn=0) for origin in relabeled.provenance[row_hash(row)]]
    assert 'invalid_turn' in gates.check(row, earlier)
    forged = dict(record, actions=[*record['actions'][:-1], student[1 + 1]])
    assert gates.check(row, relabeled.provenance[row_hash(row)]) == ()
    assert any('replay_mismatch' in error or 'teacher_label_mismatch' in error
               for error in DecisionGates([forged], registry).check(row, relabeled.provenance[row_hash(row)]))
