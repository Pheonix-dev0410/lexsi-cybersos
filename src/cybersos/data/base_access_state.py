from cybersos.domain import AccessField, BackupCodeStorage


def base_access_state(*, owner: bool) -> dict[AccessField, object]:
    """Hidden state before a template applies its changes.

    The person owns (or, for unauthorized templates, does not own) a personal adult
    account, knows the password, has another safe device, and has no extra factor.
    """
    return {
        AccessField.ACCOUNT_OWNER: owner,
        AccessField.UNAUTHORIZED_REQUEST: False,
        AccessField.ORGANIZATION_MANAGED: False,
        AccessField.CHILD_ACCOUNT: False,
        AccessField.PHONE_AVAILABLE: False,
        AccessField.SAFE_OTHER_DEVICE: True,
        AccessField.ACTIVE_SESSION_ELSEWHERE: False,
        AccessField.PASSWORD_KNOWN: True,
        AccessField.BACKUP_CODE_EXISTS: False,
        AccessField.BACKUP_CODE_ACCESSIBLE_NOW: False,
        AccessField.BACKUP_CODE_STORAGE: BackupCodeStorage.UNKNOWN,
        AccessField.INDEPENDENT_PASSKEY_EXISTS: False,
        AccessField.INDEPENDENT_PASSKEY_AVAILABLE: False,
        AccessField.ENROLLED_SECURITY_KEY_EXISTS: False,
        AccessField.ENROLLED_SECURITY_KEY_AVAILABLE: False,
        AccessField.ALTERNATE_NUMBER_EXISTS: False,
        AccessField.ALTERNATE_NUMBER_ACCESSIBLE: False,
        AccessField.ALTERNATE_NUMBER_ON_LOST_PHONE: False,
        AccessField.RECOVERY_EMAIL_EXISTS: False,
        AccessField.RECOVERY_EMAIL_ACCESSIBLE: False,
        AccessField.REAUTHENTICATION_AVAILABLE: False,
        AccessField.ACCOUNT_ACCESS_AVAILABLE: False,
        AccessField.DEVICE_POWERED: False,
        AccessField.DEVICE_ONLINE: False,
        AccessField.DEVICE_SIGNED_IN: False,
        AccessField.FIND_HUB_ENABLED: False,
        AccessField.VISIBLE_ON_GOOGLE_PLAY: False,
        AccessField.DEVICE_ERASED: False,
    }


def counterfactual_value(field: AccessField, available: bool) -> object:
    """The hidden value that makes `field` usable (or not) as a recovery factor."""
    if field == AccessField.BACKUP_CODE_STORAGE:
        return BackupCodeStorage.INDEPENDENT if available else BackupCodeStorage.SAME_LOCKED_ACCOUNT
    if field == AccessField.ALTERNATE_NUMBER_ON_LOST_PHONE:
        return not available
    return available
