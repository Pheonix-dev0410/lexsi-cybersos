from dataclasses import dataclass
from typing import Mapping

from cybersos.domain import AccessField, Availability, Incident, Provider


@dataclass(frozen=True)
class AnswerBranch:
    field: AccessField
    answer: Availability


@dataclass(frozen=True)
class Question:
    field: AccessField
    skip_if: tuple[AnswerBranch, ...] = ()


@dataclass(frozen=True)
class QuestionSection:
    questions: tuple[Question, ...]
    skip_if: tuple[AnswerBranch, ...] = ()
    recommend_steps: tuple[str, ...] = ()


NOT_OWNER = (AnswerBranch(AccessField.ACCOUNT_OWNER, Availability.FALSE),)
MANAGED = NOT_OWNER + (AnswerBranch(AccessField.ORGANIZATION_MANAGED, Availability.TRUE),)
OUTSIDE_PERSONAL_SCOPE = MANAGED + (AnswerBranch(AccessField.CHILD_ACCOUNT, Availability.TRUE),)
NO_SAFE_DEVICE = OUTSIDE_PERSONAL_SCOPE + (
    AnswerBranch(AccessField.SAFE_OTHER_DEVICE, Availability.FALSE),)
NO_PASSWORD = (AnswerBranch(AccessField.PASSWORD_KNOWN, Availability.FALSE),)

INTAKE = QuestionSection((
    Question(AccessField.ACCOUNT_OWNER),
    Question(AccessField.ORGANIZATION_MANAGED, NOT_OWNER),
    Question(AccessField.CHILD_ACCOUNT, MANAGED),
    Question(AccessField.SAFE_OTHER_DEVICE, OUTSIDE_PERSONAL_SCOPE),
), recommend_steps=('managed_account_boundary', 'child_account_boundary'))
CREDENTIALS = QuestionSection((Question(AccessField.PASSWORD_KNOWN),), NO_SAFE_DEVICE)
PASSKEY = QuestionSection((Question(AccessField.INDEPENDENT_PASSKEY_AVAILABLE, (
    AnswerBranch(AccessField.INDEPENDENT_PASSKEY_EXISTS, Availability.FALSE),)),),
    NO_SAFE_DEVICE, ('use_independent_passkey',))
BACKUP_CODE = QuestionSection((
    Question(AccessField.BACKUP_CODE_EXISTS),
    Question(AccessField.BACKUP_CODE_ACCESSIBLE_NOW, (
        AnswerBranch(AccessField.BACKUP_CODE_EXISTS, Availability.FALSE),)),
), NO_SAFE_DEVICE + NO_PASSWORD, ('use_accessible_backup_code',))
SECURITY_KEY = QuestionSection((Question(AccessField.ENROLLED_SECURITY_KEY_AVAILABLE, (
    AnswerBranch(AccessField.ENROLLED_SECURITY_KEY_EXISTS, Availability.FALSE),)),),
    NO_SAFE_DEVICE + NO_PASSWORD, ('use_security_key',))
ALTERNATE_NUMBER = QuestionSection((Question(AccessField.ALTERNATE_NUMBER_ACCESSIBLE, (
    AnswerBranch(AccessField.ALTERNATE_NUMBER_EXISTS, Availability.FALSE),)),),
    NO_SAFE_DEVICE + NO_PASSWORD, ('use_alternate_number',))
PHONE = QuestionSection((
    Question(AccessField.PHONE_AVAILABLE),
    Question(AccessField.DEVICE_SIGNED_IN, (
        AnswerBranch(AccessField.PHONE_AVAILABLE, Availability.FALSE),)),
), NO_SAFE_DEVICE + NO_PASSWORD, ('use_available_phone',))
SESSION = QuestionSection((
    Question(AccessField.ACTIVE_SESSION_ELSEWHERE),
    Question(AccessField.REAUTHENTICATION_AVAILABLE, (
        AnswerBranch(AccessField.ACTIVE_SESSION_ELSEWHERE, Availability.FALSE),)),
), NO_SAFE_DEVICE, ('use_trusted_session',))
PROTECTIVE_STEPS = ('change_exposed_password', 'review_security_activity',
                    'review_signed_in_devices', 'enable_second_factor')
PROTECTION = QuestionSection((
    Question(AccessField.ACCOUNT_ACCESS_AVAILABLE),
    Question(AccessField.REAUTHENTICATION_AVAILABLE, (
        AnswerBranch(AccessField.ACCOUNT_ACCESS_AVAILABLE, Availability.FALSE),)),
), NO_SAFE_DEVICE, PROTECTIVE_STEPS)
ANDROID_DEVICE = QuestionSection((
    Question(AccessField.ACCOUNT_ACCESS_AVAILABLE),
    Question(AccessField.DEVICE_ERASED),
    Question(AccessField.DEVICE_POWERED),
    Question(AccessField.DEVICE_ONLINE),
    Question(AccessField.DEVICE_SIGNED_IN),
    Question(AccessField.FIND_HUB_ENABLED),
    Question(AccessField.VISIBLE_ON_GOOGLE_PLAY),
), NO_SAFE_DEVICE, ('secure_android_device',))

# Each section is a fixed wizard page; its supported route ends intake early.
# Negative answers prune dependents; unknown answers keep later alternatives open.
QUESTION_FLOWS: Mapping[tuple[Provider, Incident], tuple[QuestionSection, ...]] = {
    (Provider.GOOGLE_PERSONAL, Incident.LOST_PHONE): (
        INTAKE, CREDENTIALS, PASSKEY, BACKUP_CODE, SECURITY_KEY, ALTERNATE_NUMBER,
        PHONE, SESSION, PROTECTION),
    (Provider.GOOGLE_PERSONAL, Incident.LOST_SECOND_FACTOR): (
        INTAKE, CREDENTIALS, PASSKEY, BACKUP_CODE, SECURITY_KEY, ALTERNATE_NUMBER, PHONE, SESSION),
    (Provider.GOOGLE_PERSONAL, Incident.LOCKOUT): (
        INTAKE, CREDENTIALS, PASSKEY, BACKUP_CODE, SECURITY_KEY, ALTERNATE_NUMBER, PHONE, SESSION),
    (Provider.GOOGLE_PERSONAL, Incident.EXPOSED_PASSWORD): (
        INTAKE, PROTECTION, CREDENTIALS, PASSKEY, BACKUP_CODE, SECURITY_KEY,
        ALTERNATE_NUMBER, PHONE, SESSION),
    (Provider.ANDROID, Incident.LOST_PHONE): (INTAKE, ANDROID_DEVICE),
    (Provider.ANDROID, Incident.LOCKOUT): (INTAKE,),
}
