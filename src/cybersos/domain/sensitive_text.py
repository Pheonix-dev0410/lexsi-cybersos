import re


SECRET_TERM_PATTERN = (
    r'(?:password|verification[ _-]?code|backup[ _-]?code|session[ _-]?token|'
    r'identity[ _-]?document)')

URL_PLACEHOLDER = '[model-written URL removed]'

_URL = re.compile(r'https?://|www\.|[a-z0-9-]+\.(?:com|net|org|io)/', re.I)
# Stops at quotes and backslashes so a URL inside JSON text is replaced without breaking the JSON.
_URL_TOKEN = re.compile(r'(?:https?://|www\.|[a-z0-9.-]+\.(?:com|net|org|io)/)[^\s"\'<>\\]*', re.I)


def contains_url(text: str) -> bool:
    return _URL.search(text) is not None


def replace_urls(text: str) -> str:
    return _URL_TOKEN.sub(URL_PLACEHOLDER, text)
