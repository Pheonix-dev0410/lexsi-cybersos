import re
from dataclasses import asdict, dataclass
from pathlib import Path

from cybersos.project_paths import CONFIGS_DIR, PROJECT_ROOT
from cybersos.serialization import canonical_json_sha256, file_sha256, write_json


MODEL_ID = 'CohereLabs/tiny-aya-global'


def require_immutable_revision(revision: str) -> None:
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('An immutable 40-character Hub commit SHA is required')


def adapter_hash(path: str | Path) -> str:
    root = Path(path)
    files = sorted(file for file in root.rglob('*') if file.is_file())
    if not (root / 'adapter_config.json').is_file() or not any(
            file.name in {'adapter_model.safetensors', 'adapter_model.bin'} or
            file.name.startswith('adapter_model-') for file in files):
        raise ValueError('Adapter must include configuration and model weights')
    return canonical_json_sha256({file.relative_to(root).as_posix(): file_sha256(file) for file in files})


@dataclass(frozen=True)
class ModelIdentity:
    model_id: str
    base_revision: str
    adapter_hash: str | None = None

    def __post_init__(self) -> None:
        require_immutable_revision(self.base_revision)

    def as_dict(self) -> dict[str, str | None]:
        return asdict(self)


def snapshot_base_model(*, model_id: str = MODEL_ID, revision: str | None = None,
                        local_dir: str | Path = PROJECT_ROOT / 'artifacts/base',
                        manifest_path: str | Path = CONFIGS_DIR / 'base_model.json') -> dict[str, str]:
    """Resolve a Hub commit once, snapshot it, and record portable base identity."""
    from huggingface_hub import HfApi, snapshot_download

    resolved = revision or HfApi().model_info(model_id).sha
    if not resolved:
        raise ValueError('No immutable model revision returned')
    require_immutable_revision(resolved)
    model_path = snapshot_download(repo_id=model_id, revision=resolved, local_dir=str(local_dir))
    record = {'model_id': model_id, 'revision': resolved, 'local_path': str(model_path)}
    write_json(manifest_path, record)
    return record
