"""GPU stages of the CyberSOS pipeline on Modal.

Each job runs an existing project script unchanged; outputs land on the `cybersos-artifacts`
volume. Example: `modal run deploy/modal/cybersos_jobs.py::diagnose_base`.
"""
import os
import subprocess
import sys

import modal

from modal_resources import GPU, REPO, VOLUME_BACKED_PATHS, VOLUME_ROOT, huggingface, image, volume


app = modal.App('cybersos', image=image)
BASE_DIR = f'{VOLUME_ROOT}/{VOLUME_BACKED_PATHS["artifacts/base"]}'
BASE_MANIFEST = ('--base-manifest', 'configs/base_model.json')
GPU_JOB = dict(gpu=GPU, volumes={VOLUME_ROOT: volume}, secrets=[huggingface])


def _link_outputs_to_volume() -> None:
    for relative, stored in VOLUME_BACKED_PATHS.items():
        target, link = f'{VOLUME_ROOT}/{stored}', f'{REPO}/{relative}'
        os.makedirs(target, exist_ok=True)
        os.makedirs(os.path.dirname(link), exist_ok=True)
        if os.path.isdir(link) and not os.path.islink(link):
            subprocess.run(['cp', '-rn', f'{link}/.', target], check=True)
            subprocess.run(['rm', '-rf', link], check=True)
        if not os.path.islink(link):
            os.symlink(target, link)


def _run_script(*arguments: str) -> None:
    _link_outputs_to_volume()
    try:
        subprocess.run([sys.executable, *arguments], cwd=REPO, check=True)
    finally:
        volume.commit()


@app.function(volumes={VOLUME_ROOT: volume}, secrets=[huggingface], timeout=3600)
def resolve_runtime(revision: str) -> dict[str, str]:
    """Snapshot the pinned base revision and report the values the serving contract freezes."""
    from importlib.metadata import version

    from transformers import AutoTokenizer

    from cybersos.policy import chat_template_sha256, snapshot_base_model
    from cybersos.serialization import write_json

    record = snapshot_base_model(revision=revision, local_dir=BASE_DIR,
                                 manifest_path=f'{VOLUME_ROOT}/base_model.json')
    tokenizer = AutoTokenizer.from_pretrained(BASE_DIR)
    resolved = {**record, 'chat_template_sha256': chat_template_sha256(tokenizer),
                'transformers_version': version('transformers'), 'torch_version': version('torch')}
    # Detached runs print nothing locally, so the values are kept on the volume for `modal volume get`.
    write_json(f'{VOLUME_ROOT}/resolved_runtime.json', resolved)
    volume.commit()
    return resolved


@app.function(**GPU_JOB, timeout=4 * 3600)
def doctor(stage: str = 'inference') -> None:
    _run_script('scripts/doctor.py', '--stage', stage, *BASE_MANIFEST)


@app.function(**GPU_JOB, timeout=4 * 3600)
def diagnose_base() -> None:
    _run_script('scripts/diagnose_baseline.py', '--include-base', *BASE_MANIFEST)


@app.function(volumes={VOLUME_ROOT: volume}, timeout=3600)
def render_training_file() -> None:
    _run_script('scripts/render_decisions.py', '--tokenizer', BASE_DIR)


@app.function(**GPU_JOB, timeout=6 * 3600)
def train_sft(smoke: bool = True, output_dir: str = '') -> None:
    # Adapters are never overwritten, so each run that keeps its predecessor names a new directory.
    output = output_dir or ('runs/sft-smoke' if smoke else '')
    _run_script('scripts/train_sft.py', '--config', 'configs/sft.yaml',
                *(['--smoke'] if smoke else []), *(['--output-dir', output] if output else []))


@app.function(**GPU_JOB, timeout=8 * 3600)
def evaluate(split: str, checkpoint: str, policy_label: str = '') -> None:
    _run_script('scripts/evaluate.py', '--split', split, '--checkpoint', checkpoint, *BASE_MANIFEST,
                *(['--policy-label', policy_label] if policy_label else []))


@app.function(**GPU_JOB, timeout=8 * 3600)
def train_agent(smoke: bool = True) -> None:
    _run_script('scripts/train_agent.py', '--config', 'configs/agent.yaml',
                *(['--smoke', '--output-dir', 'runs/agent-smoke'] if smoke else []))
