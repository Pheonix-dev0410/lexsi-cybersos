from collections.abc import Callable

import pytest

from cybersos.data.diagnostic_scenarios import DiagnosticCase, load_diagnostic_scenarios
from cybersos.playbooks import PlaybookRegistry
from cybersos.project_paths import DIAGNOSTIC_CASES_PATH
from cybersos.runtime import EpisodeTrace, Policy, run_episode
from cybersos.simulator import RecoveryEnvironment


@pytest.fixture(scope='session')
def cases() -> tuple[DiagnosticCase, ...]:
    return load_diagnostic_scenarios(DIAGNOSTIC_CASES_PATH)


@pytest.fixture
def run_case(registry: PlaybookRegistry) -> Callable[[DiagnosticCase, Policy], EpisodeTrace]:
    def run(case: DiagnosticCase, policy: Policy) -> EpisodeTrace:
        environment = RecoveryEnvironment(case.scenario, registry, episode_id=case.scenario.scenario_id)
        return run_episode(policy, environment)
    return run
