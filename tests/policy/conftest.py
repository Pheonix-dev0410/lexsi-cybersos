from collections.abc import Callable

import pytest

from cybersos.domain import Scenario
from cybersos.playbooks import PlaybookRegistry
from cybersos.simulator import RecoveryEnvironment


@pytest.fixture
def policy_env(registry: PlaybookRegistry) -> Callable[..., RecoveryEnvironment]:
    def create(**changes: object) -> RecoveryEnvironment:
        values = {'scenario_id': 'HIDDEN_GOLD_SPLIT_SENTINEL', 'provider': 'google_personal',
                  'incident': 'lost_phone', 'account_owner': True, 'access': {},
                  'provider_script': {'HIDDEN_PROVIDER_SCRIPT': 'denial'},
                  'objective': 'simulated_access_restored', 'opening_message': 'I lost my phone.'}
        values.update(changes)
        return RecoveryEnvironment(Scenario.from_mapping(values), registry, episode_id='opaque')

    return create
