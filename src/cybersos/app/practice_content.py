from dataclasses import dataclass, replace

from cybersos.app.access_questions import access_label
from cybersos.app.app_assets import AppAssets
from cybersos.app.incident_content import OfficialLink, official_links
from cybersos.domain import AccessField, ObservedFacts, Scenario, TerminalState
from cybersos.oracle import Reachability, reachable_routes
from cybersos.playbooks import evaluate_prerequisites


PROFILE_CHOICES = [('One phone for both methods', 'single_phone'),
                   ('Phone plus an independent passkey', 'independent')]
FACTOR_CHOICES = [('Main phone', 'phone'), ('Independent passkey device', 'passkey')]
REMOVABLE_FACTORS = {'phone': AccessField.PHONE_AVAILABLE, 'passkey': AccessField.INDEPENDENT_PASSKEY_AVAILABLE}
ROUTE_TITLES = {
    'use_available_phone': 'Signed-in main phone',
    'use_alternate_number': 'Enrolled alternate number',
    'use_independent_passkey': 'Independent passkey',
    'official_account_recovery': 'Official Google account recovery',
}


@dataclass(frozen=True)
class PracticeContent:
    profile: str
    before_routes: tuple[str, ...]
    after_routes: tuple[str, ...]
    gap: str
    preparation: str
    sources: tuple[OfficialLink, ...]


def practice_profile(assets: AppAssets, key: str) -> Scenario:
    if key not in {'single_phone', 'independent'}:
        raise ValueError('Unknown synthetic profile')
    scenario = assets.demos['preparedness']
    if key == 'independent':
        access = dict(scenario.access) | {AccessField.INDEPENDENT_PASSKEY_EXISTS: True,
                                         AccessField.INDEPENDENT_PASSKEY_AVAILABLE: True}
        scenario = replace(scenario, access=access, initial_facts=access)
    return scenario


def _route_labels(result: Reachability) -> tuple[str, ...]:
    return tuple(sorted({
        f'{" → ".join(ROUTE_TITLES.get(step, step.replace("_", " ")) for step in route.step_ids)}: '
        f'{route.terminal_state.value.replace("_", " ")}'
        for route in result.routes if len(route.step_ids) == 1}))


def _direct_restorations(result: Reachability) -> set[str]:
    return {route.step_ids[0] for route in result.routes
            if len(route.step_ids) == 1 and route.terminal_state == TerminalState.SIMULATED_ACCESS_RESTORED}


def practice_content(assets: AppAssets, profile_key: str = 'single_phone',
                     removed_factor: str = 'phone') -> PracticeContent:
    scenario = practice_profile(assets, profile_key)
    field = REMOVABLE_FACTORS[removed_factor]
    reduced = replace(scenario, access=dict(scenario.access) | {field: False}, initial_facts={})
    before = reachable_routes(scenario, assets.registry, max_steps=2)
    after = reachable_routes(reduced, assets.registry, max_steps=2)
    lost = _direct_restorations(before) - _direct_restorations(after)
    facts = ObservedFacts.from_mapping(reduced.access)
    details = []
    for step in sorted(lost):
        result = evaluate_prerequisites(assets.registry.rules[step], facts)
        details.append(f'{ROUTE_TITLES[step]}: unavailable '
                       f'{", ".join(access_label(field).lower() for field in result.blocked_fields)}')
    gap = ('The signed-in phone and alternate number both depend on this phone. '
           if {'use_available_phone', 'use_alternate_number'} <= lost else '')
    gap += '\n'.join(details) or 'No listed direct recovery route was lost in this drill.'
    if not after.reaches(TerminalState.SIMULATED_ACCESS_RESTORED):
        gap += '\nNo direct recovery route remains; official recovery can still be pending.'
    return PracticeContent(
        'Synthetic profile only. No account is connected. Sign-in prompts and both SIMs use one phone.'
        + (' An enrolled independent passkey is also available.' if profile_key == 'independent' else ''),
        _route_labels(before), _route_labels(after), gap,
        'While you still have access, follow Google’s 2-Step Verification instructions to configure '
        'an independent method, such as an enrolled security key or backup codes stored outside '
        'the account and main phone. Never share their values here.',
        official_links(assets.registry, ('google_2sv',)))
