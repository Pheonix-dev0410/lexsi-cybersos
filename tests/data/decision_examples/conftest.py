import pytest

from cybersos.data.decision_examples import DecisionExamples, build_decision_examples
from cybersos.data.root_generation import generate_roots
from cybersos.data.scenario_records import ScenarioEpisode, Split
from cybersos.data.scenario_wording import render_episodes
from cybersos.playbooks import PlaybookRegistry


@pytest.fixture(scope='module')
def training_episodes() -> tuple[ScenarioEpisode, ...]:
    roots = generate_roots()
    first = next(root for root in roots if root.pair_id)
    pair = tuple(root for root in roots if root.pair_id == first.pair_id)
    return tuple(episode for root in pair for episode in render_episodes(root, Split.TRAIN, seed=20261113))


@pytest.fixture(scope='module')
def examples(training_episodes: tuple[ScenarioEpisode, ...],
             registry: PlaybookRegistry) -> DecisionExamples:
    examples = build_decision_examples(training_episodes, registry)
    assert len(examples.trajectories) == 2
    assert not examples.exclusions
    return examples
