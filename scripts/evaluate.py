import argparse
import json
from pathlib import Path

from cybersos.evaluation.evaluation_command import evaluate
from cybersos.project_paths import CONFIGS_DIR, REPORTS_DIR, SCENARIOS_DIR, SERVING_CONTRACT_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description='Evaluate base or a local PEFT adapter through one frozen runner.')
    parser.add_argument('--config', type=Path, default=CONFIGS_DIR / 'eval.yaml')
    parser.add_argument('--contract', type=Path, default=SERVING_CONTRACT_PATH)
    parser.add_argument('--split', required=True, choices=('dev', 'test'))
    parser.add_argument('--checkpoint', required=True, help='base, a local adapter directory, Q, or R')
    parser.add_argument('--policy-label', choices=('B1', 'B2', 'B3'), default='B1')
    parser.add_argument('--cases', type=Path, help='Defaults to data/scenarios/SPLIT.jsonl')
    parser.add_argument('--output', type=Path, default=REPORTS_DIR / 'runs')
    parser.add_argument('--base-manifest', type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(args.config, args.contract, args.cases or SCENARIOS_DIR / f'{args.split}.jsonl',
                          args.output, split=args.split, checkpoint=args.checkpoint,
                          policy_label=args.policy_label, base_manifest=args.base_manifest)
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        parser.exit(1, f'evaluation failed: {error}\n')
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
