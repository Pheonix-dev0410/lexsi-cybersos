from dataclasses import replace

from cybersos.data.decision_examples import build_decision_examples
from cybersos.data.root_generation import generate_roots
from cybersos.data.scenario_records import Split
from cybersos.data.scenario_wording import render_episodes
from cybersos.domain import TerminalState
from cybersos.playbooks import PlaybookRegistry


def test_unsuccessful_trajectory_never_becomes_desired_output(training_episodes: tuple,
                                                           registry: PlaybookRegistry) -> None:
    episode = training_episodes[0]
    impossible = replace(episode, scenario=replace(episode.scenario,
                          objective=TerminalState.SIMULATED_ACCESS_RESTORED))
    examples = build_decision_examples((impossible,), registry)
    assert not examples.rows and not examples.provenance and not examples.trajectories
    assert len(examples.exclusions) == 1


def test_sensitive_synthetic_input_is_not_persisted(training_episodes: tuple,
                                                  registry: PlaybookRegistry) -> None:
    episode = training_episodes[0]
    sensitive = replace(episode, scenario=replace(episode.scenario,
                        opening_message='My email is person@example.com. Help with recovery.'))
    examples = build_decision_examples((sensitive,), registry)
    assert not examples.rows and not examples.provenance and not examples.trajectories
    assert examples.exclusions[0]['reason'] == 'sensitive_training_input'
    assert 'person@example.com' not in str(examples.exclusions)


def test_honest_limitation_is_taught_from_observed_facts(registry: PlaybookRegistry) -> None:
    root = next(root for root in generate_roots() if root.template_id == 'provider_denial')
    [episode, *_] = render_episodes(root, Split.TRAIN, seed=20261113)
    examples = build_decision_examples((episode,), registry)
    [trajectory] = examples.trajectories
    assert trajectory['teacher'] == 'observed_state_planner'
    assert trajectory['terminal_state'] == TerminalState.NO_SUPPORTED_PATH_KNOWN
