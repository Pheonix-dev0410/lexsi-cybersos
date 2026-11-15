import argparse
import json
from pathlib import Path

from cybersos.evaluation.diagnostic_command import diagnose
from cybersos.project_paths import DIAGNOSTIC_CASES_PATH, REPORTS_DIR, SERVING_CONTRACT_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description='Run all 36 development diagnostic cases through Q/R.')
    parser.add_argument('--contract', type=Path, default=SERVING_CONTRACT_PATH)
    parser.add_argument('--cases', type=Path, default=DIAGNOSTIC_CASES_PATH)
    parser.add_argument('--output', type=Path, default=REPORTS_DIR)
    parser.add_argument('--include-base', action='store_true', help='Also run B0; requires resolved model access.')
    parser.add_argument('--base-manifest', type=Path)
    args = parser.parse_args()
    try:
        result = diagnose(args.contract, args.cases, args.output, include_base=args.include_base,
                          base_manifest=args.base_manifest)
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        parser.exit(1, f'diagnostic failed: {error}\n')
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
