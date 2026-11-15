from cybersos.domain import AccessField, BackupCodeStorage


QUESTIONS: dict[AccessField, str] = {
    AccessField.ACCOUNT_OWNER: 'Is this your own account?',
    AccessField.UNAUTHORIZED_REQUEST: 'Are you trying to access an account without its owner’s permission?',
    AccessField.ORGANIZATION_MANAGED: 'Is this account managed by an organization?',
    AccessField.CHILD_ACCOUNT: 'Is this a supervised child account?',
    AccessField.PHONE_AVAILABLE: 'Do you have the main phone with you?',
    AccessField.SAFE_OTHER_DEVICE: 'Can you use another device you trust?',
    AccessField.ACTIVE_SESSION_ELSEWHERE: 'Is your account still signed in on another device?',
    AccessField.PASSWORD_KNOWN: 'Do you know your password? Answer only yes or no; never enter it here.',
    AccessField.BACKUP_CODE_EXISTS: 'Have you previously saved backup codes? Do not share any code.',
    AccessField.BACKUP_CODE_ACCESSIBLE_NOW:
        'Can you access a saved backup code outside the locked account? Do not share it.',
    AccessField.BACKUP_CODE_STORAGE: 'Where are the saved backup codes stored? Select a category only.',
    AccessField.INDEPENDENT_PASSKEY_EXISTS: 'Have you enrolled a passkey on an independent device?',
    AccessField.INDEPENDENT_PASSKEY_AVAILABLE: 'Can you use that independent passkey now?',
    AccessField.ENROLLED_SECURITY_KEY_EXISTS: 'Have you enrolled a physical security key?',
    AccessField.ENROLLED_SECURITY_KEY_AVAILABLE: 'Can you use your enrolled security key now?',
    AccessField.ALTERNATE_NUMBER_EXISTS: 'Have you enrolled an alternate phone number?',
    AccessField.ALTERNATE_NUMBER_ACCESSIBLE: 'Can you receive messages at that enrolled alternate number?',
    AccessField.ALTERNATE_NUMBER_ON_LOST_PHONE: 'Is the alternate number’s SIM also in the missing phone?',
    AccessField.RECOVERY_EMAIL_EXISTS: 'Have you configured a recovery email address? Do not enter the address.',
    AccessField.RECOVERY_EMAIL_ACCESSIBLE: 'Can you open that recovery email account?',
    AccessField.REAUTHENTICATION_AVAILABLE:
        'Can you complete any additional verification requested by Google? Do not share it.',
    AccessField.ACCOUNT_ACCESS_AVAILABLE: 'Can you currently open your Google Account?',
    AccessField.DEVICE_POWERED: 'Is the missing Android device powered on?',
    AccessField.DEVICE_ONLINE: 'Is the missing Android device online?',
    AccessField.DEVICE_SIGNED_IN: 'Is the Android device signed in to your account?',
    AccessField.FIND_HUB_ENABLED: 'Was Find Hub enabled on the Android device?',
    AccessField.VISIBLE_ON_GOOGLE_PLAY: 'Is the Android device visible in Google Play?',
    AccessField.DEVICE_ERASED: 'Has the Android device already been erased?',
}

AVAILABILITY_CHOICES = [('Yes', 'true'), ('No', 'false'), ('I don’t know', 'unknown')]
STORAGE_CHOICES = [
    ('Outside the locked account', BackupCodeStorage.INDEPENDENT.value),
    ('Inside the same locked account', BackupCodeStorage.SAME_LOCKED_ACCOUNT.value),
    ('I don’t know', BackupCodeStorage.UNKNOWN.value),
]


def answer_choices(field: AccessField) -> list[tuple[str, str]]:
    return STORAGE_CHOICES if field == AccessField.BACKUP_CODE_STORAGE else AVAILABILITY_CHOICES


def access_label(field: AccessField) -> str:
    return field.value.replace('_', ' ').capitalize()


def availability_label(value: str) -> str:
    return {'true': 'Yes', 'false': 'No', 'unknown': 'Not known',
            'independent': 'Outside the locked account',
            'same_locked_account': 'Inside the same locked account'}[value]
