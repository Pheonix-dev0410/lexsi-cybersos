from pathlib import Path

import modal


REPO = '/root/lexsi_hack'
# In the container this file sits in /root, where the local checkout layout does not exist.
LOCAL_ROOT = Path(__file__).resolve().parents[2] if modal.is_local() else Path(REPO)
VOLUME_ROOT = '/vol'
GPU = 'H200'

volume = modal.Volume.from_name('cybersos-artifacts', create_if_missing=True)
huggingface = modal.Secret.from_name('cybersos-huggingface')

_SKIP = ['**/__pycache__', '**/*.pyc', '**/.git', '**/.pytest_cache']

# Heavy, rarely changing layers first so code edits never rebuild the GPU stack.
image = (
    modal.Image.debian_slim(python_version='3.12')
    .apt_install('git')
    .pip_install('uv')
    .add_local_dir(LOCAL_ROOT / 'vendor', f'{REPO}/vendor', copy=True, ignore=_SKIP)
    # uv resolves the combined AlignTune + AgentTune pins in seconds; pip backtracks for hours.
    .run_commands(
        'uv pip install --system torch==2.11.0 '
        f'-e {REPO}/vendor/aligntune -e {REPO}/vendor/AgentTune '
        f'-e {REPO}/vendor/CuratorKIT -e {REPO}/vendor/AuditKIT')
    .env({'PYTHONPATH': f'{REPO}/src', 'HF_XET_HIGH_PERFORMANCE': '1',
          'TOKENIZERS_PARALLELISM': 'false'})
    .add_local_dir(LOCAL_ROOT / 'src', f'{REPO}/src', ignore=_SKIP)
    .add_local_dir(LOCAL_ROOT / 'scripts', f'{REPO}/scripts', ignore=_SKIP)
    .add_local_dir(LOCAL_ROOT / 'configs', f'{REPO}/configs', ignore=_SKIP)
    .add_local_dir(LOCAL_ROOT / 'data', f'{REPO}/data', ignore=_SKIP + ['rendered'])
    .add_local_dir(LOCAL_ROOT / 'patches', f'{REPO}/patches', ignore=_SKIP)
    # The rollout patch check verifies AgentTune's pinned commit with git, so its history ships too.
    .add_local_dir(LOCAL_ROOT / 'vendor/AgentTune/.git', f'{REPO}/vendor/AgentTune/.git')
    .add_local_python_source('modal_resources')
)

# Generated outputs live on the volume; the repository paths the scripts already use point there.
# Repo path -> volume path. Outputs survive the container, and the base snapshot is shared by every job.
VOLUME_BACKED_PATHS = {'reports': 'reports', 'runs': 'runs', 'data/rendered': 'data/rendered',
                       'artifacts/base': 'base'}
