import argparse
import json
from pathlib import Path

from cybersos.data.decision_examples import build_decision_examples, save_decision_examples
from cybersos.data.on_policy_relabeling import merge_examples, relabel_student_actions
from cybersos.data.scenario_loading import load_training_episodes
from cybersos.data.scenario_records import PROFILES
from cybersos.playbooks import load_project_registry
from cybersos.project_paths import DATA_DIR, SCENARIOS_DIR
from cybersos.serialization import read_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Add DAgger rows: R labels every state a trained student reached on training scenarios')
    parser.add_argument('student_actions', type=Path, nargs='+', help='rollout_student.py outputs')
    parser.add_argument('--seed', type=int, default=20261113)
    parser.add_argument('--scenarios-dir', type=Path, default=SCENARIOS_DIR)
    parser.add_argument('--output-dir', type=Path, default=DATA_DIR / 'candidates-dagger')
    parser.add_argument('--profile', choices=PROFILES, default='full')
    args = parser.parse_args()
    registry = load_project_registry()
    episodes = load_training_episodes(args.scenarios_dir, args.profile)
    student = [record for path in args.student_actions for record in read_jsonl(path)]
    examples = merge_examples(build_decision_examples(episodes, registry),
                              relabel_student_actions(episodes, student, registry))
    print(json.dumps(save_decision_examples(
        examples, args.output_dir, seed=args.seed,
        generator='deterministic teachers (observed-state planner R, else oracle route) plus DAgger: '
                  'R relabels every state the SFT student reached, greedy and sampled; simulator replay; no LLM teacher'),
        sort_keys=True))


if __name__ == '__main__':
    main()
