import hashlib
import importlib
import subprocess
import tempfile
import types
from pathlib import Path
from typing import Any

from cybersos.project_paths import PROJECT_ROOT


AGENTTUNE_COMMIT = '1dfd054ce59e1c1bdd566cb7e5826f836b1c8c2e'
ROLLOUT_PATH = Path('src/agenttune/agentic/rollout_engines/rollout_factory.py')
VENDOR_PATH = PROJECT_ROOT / 'vendor/AgentTune'
PATCH_PATH = PROJECT_ROOT / 'patches/agenttune_cybersos_rollout.patch'


def patched_rollout_source(vendor_path: str | Path, patch_path: str | Path) -> str:
    """Check and apply the recorded diff only in a temporary copy, never in vendor."""
    vendor = Path(vendor_path).resolve()
    patch = Path(patch_path).resolve()
    revision = subprocess.run(['git', '-C', str(vendor), 'rev-parse', 'HEAD'],
                              check=True, capture_output=True, text=True).stdout.strip()
    if revision != AGENTTUNE_COMMIT:
        raise ValueError('AgentTune vendor revision differs from the recorded patch base')
    with tempfile.TemporaryDirectory(prefix='cybersos-rollout-') as directory:
        destination = Path(directory) / ROLLOUT_PATH
        destination.parent.mkdir(parents=True)
        destination.write_bytes((vendor / ROLLOUT_PATH).read_bytes())
        subprocess.run(['git', 'apply', '--check', str(patch)], cwd=directory, check=True,
                       capture_output=True, text=True)
        subprocess.run(['git', 'apply', str(patch)], cwd=directory, check=True,
                       capture_output=True, text=True)
        source = destination.read_text()
        compile(source, str(destination), 'exec')
        return source


def check_rollout_patch(vendor_path: str | Path = VENDOR_PATH,
                        patch_path: str | Path = PATCH_PATH) -> str:
    patched_rollout_source(vendor_path, patch_path)
    return hashlib.sha256(Path(patch_path).read_bytes()).hexdigest()


def load_patched_rollout_factory(vendor_path: str | Path, patch_path: str | Path) -> Any:
    source = patched_rollout_source(vendor_path, patch_path)
    upstream = importlib.import_module('agenttune.agentic.rollout_engines.rollout_factory')
    installed = Path(upstream.__file__).read_text()
    pristine = (Path(vendor_path) / ROLLOUT_PATH).read_text()
    if installed not in (pristine, source):
        raise ValueError('Installed AgentTune rollout does not match the pinned source or patch')
    patched = types.ModuleType(upstream.__name__)
    patched.__package__ = upstream.__package__
    patched.__file__ = upstream.__file__
    exec(compile(source, upstream.__file__, 'exec'), patched.__dict__)
    return patched.create_rollout_fn
