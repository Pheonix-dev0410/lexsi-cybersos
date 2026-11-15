import argparse
import json
from dataclasses import replace
from pathlib import Path

from cybersos.project_paths import CONFIGS_DIR
from cybersos.training.sft_config import load_sft_config
from cybersos.training.sft_training import train_sft


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Fine-tune a LoRA adapter on the rendered decision file with AlignTune (TRL backend)')
    parser.add_argument('--config', type=Path, default=CONFIGS_DIR / 'sft.yaml')
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--output-dir')
    args = parser.parse_args()
    config = load_sft_config(args.config)
    if args.output_dir:
        config = replace(config, output_dir=args.output_dir)
    result = train_sft(config, smoke=args.smoke)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
