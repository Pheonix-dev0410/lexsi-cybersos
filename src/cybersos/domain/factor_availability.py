from collections.abc import Callable

from cybersos.domain.access import AccessField, Availability, BackupCodeStorage, FactValue


_EXISTENCE_FIELDS = {
    AccessField.BACKUP_CODE_ACCESSIBLE_NOW: AccessField.BACKUP_CODE_EXISTS,
    AccessField.INDEPENDENT_PASSKEY_AVAILABLE: AccessField.INDEPENDENT_PASSKEY_EXISTS,
    AccessField.ENROLLED_SECURITY_KEY_AVAILABLE: AccessField.ENROLLED_SECURITY_KEY_EXISTS,
    AccessField.ALTERNATE_NUMBER_ACCESSIBLE: AccessField.ALTERNATE_NUMBER_EXISTS,
    AccessField.RECOVERY_EMAIL_ACCESSIBLE: AccessField.RECOVERY_EMAIL_EXISTS,
}


def effective_access_value(field: AccessField, read: Callable[[AccessField], FactValue]) -> FactValue:
    """Apply availability constraints without disclosing the dependency values."""
    existence = _EXISTENCE_FIELDS.get(field)
    if existence is not None and read(existence) == Availability.FALSE:
        return Availability.FALSE
    if field == AccessField.BACKUP_CODE_ACCESSIBLE_NOW and (
            read(AccessField.BACKUP_CODE_STORAGE) == BackupCodeStorage.SAME_LOCKED_ACCOUNT):
        return Availability.FALSE
    if field == AccessField.ALTERNATE_NUMBER_ACCESSIBLE and (
            read(AccessField.PHONE_AVAILABLE) == Availability.FALSE and
            read(AccessField.ALTERNATE_NUMBER_ON_LOST_PHONE) == Availability.TRUE):
        return Availability.FALSE
    return read(field)
