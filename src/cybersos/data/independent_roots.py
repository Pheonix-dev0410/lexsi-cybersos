from dataclasses import dataclass
from functools import cache

from cybersos.data.base_access_state import base_access_state, counterfactual_value
from cybersos.data.opening_facts import opening_facts
from cybersos.data.root_generation import make_root
from cybersos.serialization import canonical_json_sha256
from cybersos.data.scenario_records import Bucket, ScenarioRoot
from cybersos.data.state_templates import StateTemplate
from cybersos.domain import (
    AccessField, BackupCodeStorage, Incident, Provider, ProviderResponse, Scenario, TerminalState,
)


@dataclass(frozen=True)
class IndependentDesign:
    """A held-out decision structure authored separately from the training templater."""

    name: str
    paired_field: AccessField
    changes: tuple[tuple[AccessField, object], ...]
    opening: str
    stated: tuple[AccessField, ...]


DESIGNS = (
    IndependentDesign(
        'paper_codes_stale_session', AccessField.BACKUP_CODE_ACCESSIBLE_NOW,
        ((AccessField.BACKUP_CODE_EXISTS, True),
         (AccessField.BACKUP_CODE_STORAGE, BackupCodeStorage.INDEPENDENT),
         (AccessField.ACTIVE_SESSION_ELSEWHERE, True)),
        'I have paper recovery codes and a browser that may have expired.',
        (AccessField.BACKUP_CODE_EXISTS, AccessField.BACKUP_CODE_STORAGE,
         AccessField.ACTIVE_SESSION_ELSEWHERE)),
    IndependentDesign(
        'code_storage_with_unreachable_email', AccessField.BACKUP_CODE_STORAGE,
        ((AccessField.BACKUP_CODE_EXISTS, True), (AccessField.BACKUP_CODE_ACCESSIBLE_NOW, True),
         (AccessField.RECOVERY_EMAIL_EXISTS, True)),
        'My recovery email is unreachable and I do not know where my code file is stored.',
        (AccessField.RECOVERY_EMAIL_EXISTS, AccessField.RECOVERY_EMAIL_ACCESSIBLE,
         AccessField.BACKUP_CODE_EXISTS)),
    IndependentDesign(
        'key_with_cloud_locked_codes', AccessField.ENROLLED_SECURITY_KEY_AVAILABLE,
        ((AccessField.ENROLLED_SECURITY_KEY_EXISTS, True), (AccessField.BACKUP_CODE_EXISTS, True),
         (AccessField.BACKUP_CODE_ACCESSIBLE_NOW, True),
         (AccessField.BACKUP_CODE_STORAGE, BackupCodeStorage.SAME_LOCKED_ACCOUNT)),
        'My codes are inside the locked account; I also enrolled a physical key.',
        (AccessField.BACKUP_CODE_EXISTS, AccessField.BACKUP_CODE_STORAGE,
         AccessField.ENROLLED_SECURITY_KEY_EXISTS)),
    IndependentDesign(
        'passkey_and_dead_number', AccessField.INDEPENDENT_PASSKEY_AVAILABLE,
        ((AccessField.INDEPENDENT_PASSKEY_EXISTS, True), (AccessField.ALTERNATE_NUMBER_EXISTS, True),
         (AccessField.ALTERNATE_NUMBER_ON_LOST_PHONE, True)),
        'The old number was on my missing phone; I enrolled a passkey separately.',
        (AccessField.ALTERNATE_NUMBER_EXISTS, AccessField.ALTERNATE_NUMBER_ON_LOST_PHONE,
         AccessField.INDEPENDENT_PASSKEY_EXISTS)),
    IndependentDesign(
        'session_with_inaccessible_key', AccessField.REAUTHENTICATION_AVAILABLE,
        ((AccessField.ACTIVE_SESSION_ELSEWHERE, True), (AccessField.ENROLLED_SECURITY_KEY_EXISTS, True)),
        'My browser session is still there but my physical key is out of reach.',
        (AccessField.ACTIVE_SESSION_ELSEWHERE, AccessField.ENROLLED_SECURITY_KEY_EXISTS,
         AccessField.ENROLLED_SECURITY_KEY_AVAILABLE)),
    IndependentDesign(
        'number_and_stale_session', AccessField.ALTERNATE_NUMBER_ON_LOST_PHONE,
        ((AccessField.ALTERNATE_NUMBER_EXISTS, True), (AccessField.ALTERNATE_NUMBER_ACCESSIBLE, True),
         (AccessField.ACTIVE_SESSION_ELSEWHERE, True)),
        'I have a signed-in browser and an alternate number whose SIM may be missing.',
        (AccessField.ACTIVE_SESSION_ELSEWHERE, AccessField.ALTERNATE_NUMBER_EXISTS)),
    IndependentDesign(
        'passkey_without_known_password', AccessField.INDEPENDENT_PASSKEY_AVAILABLE,
        ((AccessField.INDEPENDENT_PASSKEY_EXISTS, True), (AccessField.PASSWORD_KNOWN, False)),
        'I forgot the password but had set up a passkey on another device.',
        (AccessField.PASSWORD_KNOWN, AccessField.INDEPENDENT_PASSKEY_EXISTS)),
    IndependentDesign(
        'key_after_passkey_challenge', AccessField.ENROLLED_SECURITY_KEY_AVAILABLE,
        ((AccessField.ENROLLED_SECURITY_KEY_EXISTS, True), (AccessField.INDEPENDENT_PASSKEY_EXISTS, True),
         (AccessField.INDEPENDENT_PASSKEY_AVAILABLE, True)),
        'The passkey did not work. I might still have my enrolled physical key.',
        (AccessField.INDEPENDENT_PASSKEY_EXISTS, AccessField.ENROLLED_SECURITY_KEY_EXISTS)),
    IndependentDesign(
        'codes_after_key_challenge', AccessField.BACKUP_CODE_ACCESSIBLE_NOW,
        ((AccessField.BACKUP_CODE_EXISTS, True),
         (AccessField.BACKUP_CODE_STORAGE, BackupCodeStorage.INDEPENDENT),
         (AccessField.ENROLLED_SECURITY_KEY_EXISTS, True),
         (AccessField.ENROLLED_SECURITY_KEY_AVAILABLE, True)),
        'My physical key was not accepted. I also saved recovery codes.',
        (AccessField.ENROLLED_SECURITY_KEY_EXISTS, AccessField.BACKUP_CODE_EXISTS)),
    IndependentDesign(
        'session_after_code_challenge', AccessField.REAUTHENTICATION_AVAILABLE,
        ((AccessField.ACTIVE_SESSION_ELSEWHERE, True), (AccessField.BACKUP_CODE_EXISTS, True),
         (AccessField.BACKUP_CODE_ACCESSIBLE_NOW, True),
         (AccessField.BACKUP_CODE_STORAGE, BackupCodeStorage.INDEPENDENT)),
        'The saved code option did not work. A browser is still signed in.',
        (AccessField.BACKUP_CODE_EXISTS, AccessField.ACTIVE_SESSION_ELSEWHERE)),
    IndependentDesign(
        'number_after_passkey_challenge', AccessField.ALTERNATE_NUMBER_ON_LOST_PHONE,
        ((AccessField.ALTERNATE_NUMBER_EXISTS, True), (AccessField.ALTERNATE_NUMBER_ACCESSIBLE, True),
         (AccessField.INDEPENDENT_PASSKEY_EXISTS, True),
         (AccessField.INDEPENDENT_PASSKEY_AVAILABLE, True)),
        'My passkey was not accepted; I have an alternate registered number.',
        (AccessField.INDEPENDENT_PASSKEY_EXISTS, AccessField.ALTERNATE_NUMBER_EXISTS)),
    IndependentDesign(
        'passkey_after_phone_challenge', AccessField.INDEPENDENT_PASSKEY_AVAILABLE,
        ((AccessField.INDEPENDENT_PASSKEY_EXISTS, True), (AccessField.PHONE_AVAILABLE, True),
         (AccessField.DEVICE_SIGNED_IN, True)),
        'My phone prompt did not work; I also enrolled a separate passkey.',
        (AccessField.PHONE_AVAILABLE, AccessField.INDEPENDENT_PASSKEY_EXISTS)),
    IndependentDesign(
        'codes_after_number_challenge', AccessField.BACKUP_CODE_ACCESSIBLE_NOW,
        ((AccessField.BACKUP_CODE_EXISTS, True),
         (AccessField.BACKUP_CODE_STORAGE, BackupCodeStorage.INDEPENDENT),
         (AccessField.ALTERNATE_NUMBER_EXISTS, True), (AccessField.ALTERNATE_NUMBER_ACCESSIBLE, True)),
        'The alternate number option did not work. I had saved backup codes.',
        (AccessField.ALTERNATE_NUMBER_EXISTS, AccessField.BACKUP_CODE_EXISTS)),
    IndependentDesign(
        'session_without_password', AccessField.REAUTHENTICATION_AVAILABLE,
        ((AccessField.ACTIVE_SESSION_ELSEWHERE, True), (AccessField.PASSWORD_KNOWN, False),
         (AccessField.RECOVERY_EMAIL_EXISTS, True), (AccessField.RECOVERY_EMAIL_ACCESSIBLE, True)),
        'I forgot my password, but have a browser session and can open my recovery email.',
        (AccessField.PASSWORD_KNOWN, AccessField.ACTIVE_SESSION_ELSEWHERE,
         AccessField.RECOVERY_EMAIL_ACCESSIBLE)),
    IndependentDesign(
        'key_with_same_device_number', AccessField.ENROLLED_SECURITY_KEY_AVAILABLE,
        ((AccessField.ENROLLED_SECURITY_KEY_EXISTS, True), (AccessField.ALTERNATE_NUMBER_EXISTS, True),
         (AccessField.ALTERNATE_NUMBER_ACCESSIBLE, True),
         (AccessField.ALTERNATE_NUMBER_ON_LOST_PHONE, True)),
        'The registered number is on the lost phone. I might still have my physical key.',
        (AccessField.ALTERNATE_NUMBER_ON_LOST_PHONE, AccessField.ENROLLED_SECURITY_KEY_EXISTS)),
)
DESIGNS_BY_NAME = {design.name: design for design in DESIGNS}
STEP_FOR_FIELD = {
    AccessField.BACKUP_CODE_STORAGE: 'use_accessible_backup_code',
    AccessField.BACKUP_CODE_ACCESSIBLE_NOW: 'use_accessible_backup_code',
    AccessField.ENROLLED_SECURITY_KEY_AVAILABLE: 'use_security_key',
    AccessField.INDEPENDENT_PASSKEY_AVAILABLE: 'use_independent_passkey',
    AccessField.REAUTHENTICATION_AVAILABLE: 'use_trusted_session',
    AccessField.ALTERNATE_NUMBER_ON_LOST_PHONE: 'use_alternate_number',
}
CHALLENGED_STEPS = ('use_accessible_backup_code', 'use_independent_passkey', 'use_security_key',
                    'use_alternate_number', 'use_available_phone', 'use_trusted_session')


def _design_roots(design: IndependentDesign) -> tuple[ScenarioRoot, ...]:
    access = base_access_state(owner=True) | dict(design.changes)
    pair_id = canonical_json_sha256({'independent_design': design.name, 'access': access})
    template = StateTemplate(design.name, Bucket.ROUTINE, ('independent_decision_structure',),
                             design.opening, design.stated, paired_field=design.paired_field)
    # Every other factor is challenged, so only the paired field decides restoration.
    scripts: dict[str, object] = dict.fromkeys(CHALLENGED_STEPS, ProviderResponse.CHALLENGE)
    scripts |= {'recovery_attempt': ProviderResponse.PENDING_REVIEW,
                STEP_FOR_FIELD[design.paired_field]: ProviderResponse.SUCCESS}
    initial = opening_facts(access, incident=Incident.LOST_SECOND_FACTOR, stated=design.stated)
    roots = []
    for available in (False, True):
        state = access | {design.paired_field: counterfactual_value(design.paired_field, available)}
        scenario = Scenario(design.name, Provider.GOOGLE_PERSONAL, Incident.LOST_SECOND_FACTOR,
                            True, state, scripts, initial_facts=initial,
                            objective=TerminalState.SIMULATED_ACCESS_RESTORED if available else
                            TerminalState.OFFICIAL_RECOVERY_PENDING)
        roots.append(make_root(scenario, f'independent/{design.name}', template,
                               pair_id=pair_id, eligible=available, independent=True))
    return tuple(roots)


@cache
def independent_roots() -> tuple[ScenarioRoot, ...]:
    return tuple(root for design in DESIGNS for root in _design_roots(design))
