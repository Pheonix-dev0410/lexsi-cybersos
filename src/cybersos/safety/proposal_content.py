import re

from cybersos.domain.sensitive_text import SECRET_TERM_PATTERN, contains_url
from cybersos.safety.violations import Violation, ViolationKind


_SECRET_REQUEST = re.compile(
    r'\b(?:give|send|share|paste|provide|upload|tell me|enter here|collect|request|what is your)\b'
    r'.{0,45}\b' + SECRET_TERM_PATTERN + r'\b', re.I)
_SECRET_NAME = r'(?:password|verification_code|backup_code|backup_code_value|session_token|identity_document)'
_SECRET_FIELD = re.compile(r'"' + _SECRET_NAME + r'"\s*:|"field"\s*:\s*"' + _SECRET_NAME + r'"', re.I)
_NEGATION = re.compile(r"(?:never|do not|don['’]t|must not|should not)\s+$", re.I)


def content_violations(raw_text: str) -> tuple[Violation, ...]:
    violations: list[Violation] = []
    if contains_url(raw_text):
        violations.append(Violation(ViolationKind.FABRICATED_DESTINATION_OR_EVIDENCE,
                                    'Model-supplied destination'))
    solicitation = any(not _NEGATION.search(raw_text[max(0, match.start() - 20):match.start()])
                       for match in _SECRET_REQUEST.finditer(raw_text))
    if solicitation or _SECRET_FIELD.search(raw_text):
        violations.append(Violation(ViolationKind.SECRET_SOLICITATION, 'Proposed collection of a secret'))
    return tuple(violations)
