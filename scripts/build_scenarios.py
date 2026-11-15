import argparse
import json
from pathlib import Path

from cybersos.data.scenario_records import PROFILES
from cybersos.data.split_artifacts import save_scenario_splits
from cybersos.data.split_assignment import build_scenario_splits
from cybersos.project_paths import DIAGNOSTIC_CASES_PATH, SCENARIOS_DIR


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Generate scenario roots, assign them to train/dev/test, and save the frozen splits')
    parser.add_argument('--seed', type=int, default=20261113)
    parser.add_argument('--diagnostics', type=Path, default=DIAGNOSTIC_CASES_PATH)
    parser.add_argument('--output-dir', type=Path, default=SCENARIOS_DIR)
    parser.add_argument('--profile', choices=PROFILES, default='full')
    args = parser.parse_args()
    episodes = build_scenario_splits(args.diagnostics, seed=args.seed, profile=args.profile)
    manifest = save_scenario_splits(episodes, args.output_dir, seed=args.seed,
                                    allocation=PROFILES[args.profile])
    print(json.dumps({'episodes': len(episodes), 'manifest': str(manifest)}, sort_keys=True))


if __name__ == '__main__':
    main()
