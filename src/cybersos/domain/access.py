from enum import StrEnum


class Availability(StrEnum):
    TRUE = 'true'
    FALSE = 'false'
    UNKNOWN = 'unknown'

    @classmethod
    def from_value(cls, value: object) -> 'Availability':
        if isinstance(value, bool):
            return cls.TRUE if value else cls.FALSE
        return cls(value)


class AccessField(StrEnum):
    ACCOUNT_OWNER = 'account_owner'
    UNAUTHORIZED_REQUEST = 'unauthorized_request'
    ORGANIZATION_MANAGED = 'organization_managed'
    CHILD_ACCOUNT = 'child_account'
    PHONE_AVAILABLE = 'phone_available'
    SAFE_OTHER_DEVICE = 'safe_other_device'
    ACTIVE_SESSION_ELSEWHERE = 'active_session_elsewhere'
    PASSWORD_KNOWN = 'password_known'
    BACKUP_CODE_EXISTS = 'backup_code_exists'
    BACKUP_CODE_ACCESSIBLE_NOW = 'backup_code_accessible_now'
    BACKUP_CODE_STORAGE = 'backup_code_storage'
    INDEPENDENT_PASSKEY_EXISTS = 'independent_passkey_exists'
    INDEPENDENT_PASSKEY_AVAILABLE = 'independent_passkey_available'
    ENROLLED_SECURITY_KEY_EXISTS = 'enrolled_security_key_exists'
    ENROLLED_SECURITY_KEY_AVAILABLE = 'enrolled_security_key_available'
    ALTERNATE_NUMBER_EXISTS = 'alternate_number_exists'
    ALTERNATE_NUMBER_ACCESSIBLE = 'alternate_number_accessible'
    ALTERNATE_NUMBER_ON_LOST_PHONE = 'alternate_number_on_lost_phone'
    RECOVERY_EMAIL_EXISTS = 'recovery_email_exists'
    RECOVERY_EMAIL_ACCESSIBLE = 'recovery_email_accessible'
    REAUTHENTICATION_AVAILABLE = 'reauthentication_available'
    ACCOUNT_ACCESS_AVAILABLE = 'account_access_available'
    DEVICE_POWERED = 'device_powered'
    DEVICE_ONLINE = 'device_online'
    DEVICE_SIGNED_IN = 'device_signed_in'
    FIND_HUB_ENABLED = 'find_hub_enabled'
    VISIBLE_ON_GOOGLE_PLAY = 'visible_on_google_play'
    DEVICE_ERASED = 'device_erased'


class BackupCodeStorage(StrEnum):
    SAME_LOCKED_ACCOUNT = 'same_locked_account'
    INDEPENDENT = 'independent'
    UNKNOWN = 'unknown'


FactValue = Availability | BackupCodeStorage


def normalize_value(field: AccessField, value: object) -> FactValue:
    if field == AccessField.BACKUP_CODE_STORAGE:
        return BackupCodeStorage(value)
    return Availability.from_value(value)
