from typing import Callable

import pytest

from cybersos.domain import Action, Scenario, TerminalState, ToolName
from cybersos.evaluation import Adjudication, CaseInfo, Measurements, RunIdentity, TraceRecord, record_episode
from cybersos.playbooks import PlaybookRegistry
from cybersos.runtime import run_episode
from cybersos.simulator import RecoveryEnvironment


@pytest.fixture
def episode_record(registry: PlaybookRegistry) -> Callable[..., TraceRecord]:
    def create(*, episode_id: str = 'episode', scenario_id: str = 'scenario',
               root_id: str = 'root', pair_id: str | None = None,
               prefix: tuple[str, ...] = (), snapshot: bool = True) -> TraceRecord:
        facts = dict(account_owner=True, organization_managed=False, child_account=False,
                     safe_other_device=True, password_known=True, backup_code_exists=True,
                     backup_code_accessible_now=True)
        scenario = Scenario.from_mapping({
            'scenario_id': scenario_id, 'provider': 'google_personal', 'incident': 'lost_phone',
            'account_owner': True, 'access': facts, 'initial_facts': facts,
            'provider_script': {'use_accessible_backup_code': 'success'},
            'objective': 'simulated_access_restored', 'opening_message': 'I lost my phone.',
        })
        env = RecoveryEnvironment(scenario, registry, episode_id=episode_id)
        actions = iter((*prefix,
                        Action(ToolName.SIMULATE_STEP, {'step_id': 'use_accessible_backup_code'}).to_json(),
                        Action(ToolName.FINISH, {'status': 'simulated_access_restored',
                                               'next_step_id': None, 'source_ids': []}).to_json()))
        trace = run_episode(lambda observation: next(actions), env)
        case = CaseInfo(scenario_id, episode_id, root_id, TerminalState.SIMULATED_ACCESS_RESTORED,
                        eligible=True, pair_id=pair_id, slices=('legitimate',),
                        opening_message=scenario.opening_message)
        return record_episode(RunIdentity('run', 'B1', 'checkpoint', 'contract'), case, trace,
                              env.trusted_snapshot() if snapshot else None,
                              measurements=Measurements(2.0, 100, 30, len(trace.decisions), 0),
                              adjudication=Adjudication((True,)))
    return create
