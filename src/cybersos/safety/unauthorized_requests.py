import re

from cybersos.domain import AccessField, Availability, ObservedFacts


_EXPLICIT_UNAUTHORIZED = re.compile(
    r"\b(?:access|enter|recover|hack|take over)\b.{0,40}"
    r"\b(?:someone else['’]s|another person['’]s|my ex['’]s|without (?:their|the owner['’]s) permission)"
    r"|\b(?:help me|how (?:can|do) I|I want to)\b.{0,30}\bbypass\b.{0,25}"
    r"\b(?:verification|ownership checks|authentication|2fa)\b", re.I)


def is_unauthorized_request(text: str) -> bool:
    """Recognize explicit abuse requests; password mentions alone are ordinary help."""
    return bool(_EXPLICIT_UNAUTHORIZED.search(text))


def assistance_declined(facts: ObservedFacts, opening_message: str) -> bool:
    """Whether observed evidence shows the person is not acting for their own account."""
    return (is_unauthorized_request(opening_message) or
            facts.value(AccessField.UNAUTHORIZED_REQUEST) == Availability.TRUE or
            facts.value(AccessField.ACCOUNT_OWNER) == Availability.FALSE)
