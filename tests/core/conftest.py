from collections.abc import Callable

import pytest

from cybersos.domain import Scenario, SessionMode
from cybersos.playbooks import PlaybookRegistry
from cybersos.simulator import RecoveryEnvironment


@pytest.fixture
def make_env(registry: PlaybookRegistry) -> Callable[..., RecoveryEnvironment]:
    def create(*, facts: dict[str, object] | None = None,
               access: dict[str, object] | None = None,
               script: dict[str, object] | None = None,
               provider: str = 'google_personal', incident: str = 'lost_phone',
               mode: SessionMode = SessionMode.BENCHMARK, destructive: bool = False,
               required: tuple[str, ...] = (), opening: str = '',
               objective: str | None = None, owner: bool = True,
               registry_override: PlaybookRegistry | None = None,
               corrections: tuple[dict[str, object], ...] = (),
               failures: tuple[dict[str, object], ...] = (),
               answers: dict[str, object] | None = None, budget: int = 12) -> RecoveryEnvironment:
        scenario = Scenario.from_mapping({
            'scenario_id': 'scenario_1', 'provider': provider, 'incident': incident,
            'account_owner': owner, 'access': access or {}, 'initial_facts': facts or {},
            'provider_script': script or {}, 'permissions': {'destructive_actions_enabled': destructive},
            'required_protective_steps': required, 'opening_message': opening, 'objective': objective,
            'corrections': corrections, 'temporary_tool_failures': failures,
            'access_answers': answers or {},
        })
        return RecoveryEnvironment(scenario, registry_override or registry, episode_id='episode_1', mode=mode,
                                   action_budget=budget)
    return create


@pytest.fixture
def backup_facts() -> dict[str, object]:
    return dict(account_owner=True, organization_managed=False, child_account=False,
                safe_other_device=True, password_known=True, backup_code_exists=True,
                backup_code_accessible_now=True)
