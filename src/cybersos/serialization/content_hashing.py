import hashlib
import json
from collections.abc import Iterable
from pathlib import Path

from cybersos.serialization.json_values import to_json_value


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def files_sha256(paths: Iterable[str | Path]) -> str:
    """Hash of (name, content) pairs in sorted order, so listing order never changes it."""
    digest = hashlib.sha256()
    for path in sorted(Path(item) for item in paths):
        digest.update(path.name.encode())
        digest.update(file_sha256(path).encode())
    return digest.hexdigest()


def canonical_json_sha256(value: object) -> str:
    text = json.dumps(to_json_value(value), sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'))
    return hashlib.sha256(text.encode()).hexdigest()
