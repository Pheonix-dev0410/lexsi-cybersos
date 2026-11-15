from dataclasses import replace

from cybersos.baselines import PROTECTIVE_STEPS
from cybersos.data.diagnostic_scenarios import load_diagnostic_scenarios
from cybersos.domain import AccessField, Incident, ProviderResponse, Scenario, TerminalState
from cybersos.project_paths import DIAGNOSTIC_CASES_PATH


DEMO_LABELS = {
    'circular': 'A · Circular dependency',
    'containment': 'B · Useful containment',
    'preparedness': 'C · Preparedness',
}
DEMO_TEMPLATE_ID = 'public-demo-v1'


def demo_scenarios() -> dict[str, Scenario]:
    cases = {case.scenario.scenario_id: case.scenario
             for case in load_diagnostic_scenarios(DIAGNOSTIC_CASES_PATH)}
    circular = cases['codes_inside_locked_drive']
    initial = dict(circular.initial_facts)
    initial.pop(AccessField.BACKUP_CODE_STORAGE, None)
    initial.pop(AccessField.BACKUP_CODE_ACCESSIBLE_NOW, None)
    circular = replace(circular, initial_facts=initial)
    base = cases['trusted_session_denied']
    access = dict(base.access) | {AccessField.ACCOUNT_ACCESS_AVAILABLE: True}
    initial = dict(access)
    initial.pop(AccessField.REAUTHENTICATION_AVAILABLE, None)
    containment = replace(
        base, scenario_id='demo_useful_containment', incident=Incident.EXPOSED_PASSWORD,
        access=access, initial_facts=initial,
        opening_message='Synthetic demo: a password was exposed; a safe signed-in device remains.',
        required_protective_steps=PROTECTIVE_STEPS,
        provider_script={'change_exposed_password': ProviderResponse.CHALLENGE,
                         'protective_step': ProviderResponse.SUCCESS,
                         'use_trusted_session': ProviderResponse.DENIAL,
                         'official_account_recovery': ProviderResponse.PENDING_REVIEW},
        objective=TerminalState.OFFICIAL_RECOVERY_PENDING)
    base = cases['two_sims_one_lost_phone']
    access = dict(base.access) | {AccessField.PHONE_AVAILABLE: True, AccessField.DEVICE_SIGNED_IN: True}
    preparedness = replace(
        base, scenario_id='demo_single_phone', access=access, initial_facts=access,
        opening_message='Synthetic profile: sign-in prompts and both enrolled SIMs use one phone.',
        provider_script={'attempt_provider_verification': ProviderResponse.SUCCESS,
                         'official_account_recovery': ProviderResponse.PENDING_REVIEW},
        objective=TerminalState.SIMULATED_ACCESS_RESTORED)
    return {'circular': circular, 'containment': containment, 'preparedness': preparedness}
