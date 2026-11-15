import argparse
from pathlib import Path

from cybersos.evaluation.submission_inventory import check_submission
from cybersos.project_paths import PROJECT_ROOT, REPORTS_DIR


def main() -> int:
    parser = argparse.ArgumentParser(description='Inventory Section 18 artifacts and report missing submission evidence.')
    parser.add_argument('--check', action='store_true', required=True, help='Check only; does not publish or submit.')
    parser.add_argument('--root', type=Path, default=PROJECT_ROOT)
    parser.add_argument('--output', type=Path, default=REPORTS_DIR)
    args = parser.parse_args()
    try:
        result = check_submission(args.root, args.output)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f'artifact check failed: {error}\n')
    for row in result['artifacts']:
        print(f'{row["status"]}: {row["artifact"]}' + (' (optional)' if row['optional'] else ''))
    print(f'Missing required artifacts: {result["required_missing"]}; reports: {args.output}')
    return int(result['required_missing'] > 0)


if __name__ == '__main__':
    raise SystemExit(main())
