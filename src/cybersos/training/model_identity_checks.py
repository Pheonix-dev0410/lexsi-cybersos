from pathlib import Path
from typing import Any

from cybersos.policy.model_identity import MODEL_ID, require_immutable_revision
from cybersos.serialization import read_json


ADAPTER_METADATA = 'cybersos_adapter.json'


def base_identity(manifest_path: str | Path, model_path: str | Path) -> dict[str, str]:
    """Identity of the pinned local base snapshot that training starts from."""
    manifest = read_json(manifest_path)
    if manifest.get('model_id') != MODEL_ID:
        raise ValueError(f'Expected canonical model ID {MODEL_ID}')
    require_immutable_revision(manifest['revision'])
    if Path(manifest['local_path']).resolve() != Path(model_path).resolve():
        raise ValueError('Model path differs from pinned snapshot manifest')
    if not Path(model_path, 'config.json').is_file():
        raise ValueError('Pinned local model snapshot is missing')
    return {'model_id': MODEL_ID, 'base_revision': manifest['revision']}


def read_adapter_metadata(adapter_path: str | Path) -> dict[str, Any]:
    """Saved adapter metadata, refused unless it names the canonical base at a pinned revision."""
    metadata = read_json(Path(adapter_path) / ADAPTER_METADATA)
    if metadata.get('model_id') != MODEL_ID:
        raise ValueError('Adapter has the wrong canonical Hub identity')
    require_immutable_revision(metadata['base_revision'])
    return metadata
