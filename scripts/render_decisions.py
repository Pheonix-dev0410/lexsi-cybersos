import argparse
import json
from pathlib import Path

from cybersos.data.serving_budgets import load_serving_budgets
from cybersos.data.training_file_rendering import load_training_tokenizer, render_training_file
from cybersos.playbooks import load_project_registry
from cybersos.policy import load_serving_contract
from cybersos.project_paths import DATA_DIR, SERVING_CONTRACT_PATH


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Render curated decisions with the target chat template into one bounded Alpaca file')
    parser.add_argument('--tokenizer', default='CohereLabs/tiny-aya-global')
    parser.add_argument('--revision')
    parser.add_argument('--curated-dir', type=Path, default=DATA_DIR / 'curated/train')
    parser.add_argument('--output', type=Path, default=DATA_DIR / 'rendered/train_alpaca.jsonl')
    parser.add_argument('--serving-contract', type=Path, default=SERVING_CONTRACT_PATH)
    args = parser.parse_args()
    report = render_training_file(
        args.curated_dir, args.output, load_project_registry(),
        load_training_tokenizer(args.tokenizer, revision=args.revision),
        load_serving_budgets(args.serving_contract),
        end_of_turn_token=load_serving_contract(args.serving_contract).end_of_turn_token,
        tokenizer_name=args.tokenizer)
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
