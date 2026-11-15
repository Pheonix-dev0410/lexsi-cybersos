import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

from cybersos.evaluation.measured_model_policy import MeasuredModelPolicy
from cybersos.policy import load_serving_contract
from cybersos.project_paths import PROJECT_ROOT
from cybersos.serialization import read_json, write_json


def check_in_fresh_process(contract_path: Path, output: Path, *, adapter: Path | None = None,
                           base_manifest: Path | None = None) -> dict[str, Any]:
    """Load the weights in a separate interpreter, so the result cannot reuse this process's loaded state."""
    command = [sys.executable, '-m', 'cybersos.evaluation.model_load_check',
               '--contract', str(contract_path.resolve()), '--output', str(output.resolve())]
    if adapter is not None:
        command.extend(['--adapter', str(adapter.resolve())])
    if base_manifest is not None:
        command.extend(['--base-manifest', str(base_manifest.resolve())])
    checked = subprocess.run(command, capture_output=True, text=True, check=False)
    if checked.returncode:
        raise RuntimeError('Fresh-process model load failed: ' + checked.stderr[-2000:])
    return read_json(output)


def main() -> None:
    parser = argparse.ArgumentParser(description='Verify model/adapter loading in an isolated Python process.')
    parser.add_argument('--contract', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--adapter', type=Path)
    parser.add_argument('--base-manifest', type=Path)
    args = parser.parse_args()
    model = MeasuredModelPolicy(load_serving_contract(args.contract), root=PROJECT_ROOT,
                                adapter_path=args.adapter, base_manifest=args.base_manifest)
    evidence = model.load_for_check() | {'fresh_process': True,
                                        'cold_loading_seconds': model.cold_loading_seconds}
    write_json(args.output, evidence)


if __name__ == '__main__':
    main()
