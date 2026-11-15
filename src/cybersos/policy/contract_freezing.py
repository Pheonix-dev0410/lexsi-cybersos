import re
from pathlib import Path

from cybersos.policy.contract_validation import RULE_CORPORA
from cybersos.project_paths import PROJECT_ROOT, SERVING_CONTRACT_PATH
from cybersos.serialization import file_sha256, load_strict_yaml


def freeze_contract_pins(path: str | Path = SERVING_CONTRACT_PATH, *,
                         root: str | Path = PROJECT_ROOT) -> dict[str, str]:
    """Recompute every pinned corpus and guard hash from the current files.

    Only the hash values are rewritten, in place, so the rest of the contract keeps its
    authored formatting. Returns the pins whose value changed.
    """
    path, root = Path(path), Path(root)
    data = load_strict_yaml(path)
    pins = {f'{name}_sha256': file_sha256(root / data['rules'][f'{name}_path']) for name in RULE_CORPORA}
    pins |= {source: file_sha256(root / source) for source in data['guard']['files_sha256']}
    current = {f'{name}_sha256': data['rules'][f'{name}_sha256'] for name in RULE_CORPORA}
    current |= data['guard']['files_sha256']
    text = path.read_text()
    for key, digest in pins.items():
        text, count = re.subn(rf'^(\s*{re.escape(key)}:[ \t]*)\S+[ \t]*$',
                              lambda match: match.group(1) + digest, text, flags=re.M)
        if count != 1:
            raise ValueError(f'Expected exactly one pin for {key}')
    path.write_text(text)
    return {key: digest for key, digest in pins.items() if current[key] != digest}
