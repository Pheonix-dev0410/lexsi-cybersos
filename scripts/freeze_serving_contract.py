import argparse
from pathlib import Path

from cybersos.policy import freeze_contract_pins
from cybersos.project_paths import PROJECT_ROOT, SERVING_CONTRACT_PATH


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Recompute the pinned rule-corpus and guard-source hashes in the serving contract.')
    parser.add_argument('--contract', type=Path, default=SERVING_CONTRACT_PATH)
    parser.add_argument('--root', type=Path, default=PROJECT_ROOT)
    args = parser.parse_args()
    try:
        changed = freeze_contract_pins(args.contract, root=args.root)
    except (OSError, KeyError, ValueError) as error:
        parser.exit(1, f'freeze failed: {error}\n')
    for key, digest in changed.items():
        print(f'{key}: {digest}')
    print(f'{len(changed)} pin(s) updated in {args.contract}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
