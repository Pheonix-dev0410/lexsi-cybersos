import argparse
import json
from dataclasses import replace
from pathlib import Path

from cybersos.project_paths import CONFIGS_DIR
from cybersos.training.agent_config import load_agent_config
from cybersos.training.agent_training import train_agent
from cybersos.training.rollout_patch import check_rollout_patch


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Continue the SFT adapter with a bounded AgentTune GRPO pilot in the simulator')
    parser.add_argument('--config', type=Path, default=CONFIGS_DIR / 'agent.yaml')
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--check-patch', action='store_true')
    parser.add_argument('--output-dir')
    args = parser.parse_args()
    config = load_agent_config(args.config)
    if args.output_dir:
        config = replace(config, output_dir=args.output_dir)
    if args.check_patch:
        print('AgentTune patch applies cleanly; SHA256=' + check_rollout_patch(
            config.path('vendor_path'), config.path('patch_path')))
    else:
        # AgentTune's result can carry callables; they print by name rather than abort the run.
        print(json.dumps(train_agent(config, smoke=args.smoke), indent=2, allow_nan=False, default=repr))


if __name__ == '__main__':
    main()
