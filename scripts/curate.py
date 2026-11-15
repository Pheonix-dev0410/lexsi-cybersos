import argparse
import json
from pathlib import Path

from cybersos.data.curation_bridge import curate_decisions
from cybersos.data.scenario_loading import load_training_episodes
from cybersos.data.scenario_records import PROFILES
from cybersos.playbooks import load_project_registry
from cybersos.project_paths import DATA_DIR, SCENARIOS_DIR


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Gate candidate decision rows and deduplicate them with CuratorKIT')
    parser.add_argument('--seed', type=int, default=20261113)
    parser.add_argument('--scenarios-dir', type=Path, default=SCENARIOS_DIR)
    parser.add_argument('--candidate-dir', type=Path, default=DATA_DIR / 'candidates')
    parser.add_argument('--output-dir', type=Path, default=DATA_DIR / 'curated/train')
    parser.add_argument('--profile', choices=PROFILES, default='full')
    args = parser.parse_args()
    report = curate_decisions(args.candidate_dir, args.output_dir, load_project_registry(),
                              load_training_episodes(args.scenarios_dir, args.profile), seed=args.seed)
    print(json.dumps({key: report[key] for key in
                      ('input_rows', 'accepted_rows', 'rejected_rows', 'exported_rows',
                       'rejection_reasons')}, sort_keys=True))


if __name__ == '__main__':
    main()
