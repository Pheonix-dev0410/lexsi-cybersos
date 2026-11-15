from collections.abc import Iterable, Mapping

from cybersos.serialization import canonical_json_sha256
from cybersos.domain import AccessField, Incident


LOST_PHONE_DETAILS = (
    AccessField.DEVICE_POWERED, AccessField.VISIBLE_ON_GOOGLE_PLAY, AccessField.FIND_HUB_ENABLED,
    AccessField.DEVICE_ERASED, AccessField.DEVICE_SIGNED_IN,
)
SIGN_IN_DETAILS = (AccessField.RECOVERY_EMAIL_EXISTS, AccessField.RECOVERY_EMAIL_ACCESSIBLE)


def opening_facts(access: Mapping[AccessField, object], *, incident: Incident,
                  stated: Iterable[AccessField], detail: AccessField | None = None
                  ) -> dict[AccessField, object]:
    """Facts the opening message states; every other field stays unknown until asked.

    "My account" states ownership and "I lost my phone" states the phone is unavailable.
    """
    fields = [AccessField.ACCOUNT_OWNER, *stated]
    if incident == Incident.LOST_PHONE:
        fields.append(AccessField.PHONE_AVAILABLE)
    if detail is not None:
        fields.append(detail)
    return {field: access[field] for field in fields}


def volunteered_detail(key: object, incident: Incident,
                       excluded: Iterable[AccessField]) -> AccessField | None:
    """Pick at most one incident-relevant detail a person might add, seeded by `key`."""
    skipped = set(excluded)
    candidates = LOST_PHONE_DETAILS if incident == Incident.LOST_PHONE else SIGN_IN_DETAILS
    options = [field for field in candidates if field not in skipped]
    choice = int(canonical_json_sha256(key), 16) % (len(options) + 1)
    return options[choice] if choice < len(options) else None
