import re

from cybersos.data.decision_rows import Row
from cybersos.domain.sensitive_text import SECRET_TERM_PATTERN


_PATTERNS = {
    'email': r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b',
    'ip_address': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
    'personal_identity': r'\b(?:my name is|i live at|passport number|social security|aadhaar)\b',
    'secret_value': (
        r'\b' + SECRET_TERM_PATTERN + r'(?:[ _-]?value)?\b["\s]*'
        r'(?:is\s+|[:=]\s*)["\s]*[A-Z0-9+/][A-Z0-9+/=_-]{2,}'),
    'private_key': r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    'bearer_token': r'\bBearer\s+[A-Z0-9._~+/=-]{8,}',
    'jwt': r'\beyJ[A-Z0-9_-]+\.eyJ[A-Z0-9_-]+\.[A-Z0-9_-]+',
}


def privacy_errors(row: Row) -> list[str]:
    text = '\n'.join(row.values()).replace('\\"', '"').replace('\\n', '\n')
    errors = [f'privacy:{name}' for name, pattern in _PATTERNS.items()
              if re.search(pattern, text, re.I)]
    phones = re.finditer(r'(?<![\w/])\+?\d[\d ()-]{8,}\d(?!\w)', text)
    if any(sum(character.isdigit() for character in match.group()) >= 10 for match in phones):
        errors.append('privacy:phone')
    return errors
