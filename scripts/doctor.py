import argparse
import json
from pathlib import Path

from cybersos.evaluation.environment_checks import check_environment
from cybersos.project_paths import REPORTS_DIR, SERVING_CONTRACT_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description='Check stage imports, versions, CUDA, model access and serialization.')
    parser.add_argument('--stage', required=True, choices=('inference', 'data', 'align', 'agent'))
    parser.add_argument('--contract', type=Path, default=SERVING_CONTRACT_PATH)
    parser.add_argument('--output', type=Path, default=REPORTS_DIR)
    parser.add_argument('--base-manifest', type=Path)
    parser.add_argument('--adapter', type=Path, help='Verify this saved adapter reloads in a fresh process.')
    args = parser.parse_args()
    try:
        result = check_environment(args.stage, args.contract, args.output,
                                   base_manifest=args.base_manifest, adapter=args.adapter)
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        parser.exit(1, f'environment check failed: {error}\n')
    print(json.dumps(result, indent=2))
    return int(result['status'] != 'passed')


if __name__ == '__main__':
    raise SystemExit(main())
