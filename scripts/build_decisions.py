import argparse
import json
from pathlib import Path

from cybersos.data.decision_examples import build_decision_examples, save_decision_examples
from cybersos.data.scenario_loading import load_training_episodes
from cybersos.data.scenario_records import PROFILES
from cybersos.playbooks import load_project_registry
from cybersos.project_paths import DATA_DIR, SCENARIOS_DIR


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Replay reference trajectories on training scenarios into supervised decision rows')
    parser.add_argument('--seed', type=int, default=20261113)
    parser.add_argument('--scenarios-dir', type=Path, default=SCENARIOS_DIR)
    parser.add_argument('--output-dir', type=Path, default=DATA_DIR / 'candidates')
    parser.add_argument('--profile', choices=PROFILES, default='full')
    args = parser.parse_args()
    examples = build_decision_examples(load_training_episodes(args.scenarios_dir, args.profile),
                                       load_project_registry())
    print(json.dumps(save_decision_examples(examples, args.output_dir, seed=args.seed), sort_keys=True))


if __name__ == '__main__':
    main()
