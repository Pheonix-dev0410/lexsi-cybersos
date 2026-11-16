import argparse
from pathlib import Path

from cybersos.data.on_policy_relabeling import collect_student_actions
from cybersos.data.scenario_loading import load_training_episodes
from cybersos.data.scenario_records import PROFILES
from cybersos.playbooks import load_project_registry
from cybersos.policy import TransformersPolicy, load_serving_contract
from cybersos.project_paths import PROJECT_ROOT, SCENARIOS_DIR, SERVING_CONTRACT_PATH
from cybersos.serialization import write_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Run a trained adapter greedily on one shard of the training scenarios and keep its proposals')
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--shard', type=int, default=0)
    parser.add_argument('--shards', type=int, default=1)
    parser.add_argument('--base-manifest', type=Path)
    parser.add_argument('--contract', type=Path, default=SERVING_CONTRACT_PATH)
    parser.add_argument('--scenarios-dir', type=Path, default=SCENARIOS_DIR)
    parser.add_argument('--profile', choices=PROFILES, default='full')
    parser.add_argument('--temperature', type=float, help='Sample instead of greedy decoding')
    parser.add_argument('--samples', type=int, default=1)
    parser.add_argument('--seed', type=int, default=20261116)
    args = parser.parse_args()
    if not 0 <= args.shard < args.shards:
        parser.error('shard must be in [0, shards)')
    episodes = load_training_episodes(args.scenarios_dir, args.profile)[args.shard::args.shards]
    policy = TransformersPolicy(load_serving_contract(args.contract), root=PROJECT_ROOT,
                                adapter_path=args.checkpoint, base_manifest=args.base_manifest,
                                sampling_temperature=args.temperature)
    if args.temperature is not None:
        import torch
        torch.manual_seed(args.seed + args.shard)
    registry = load_project_registry()
    write_jsonl(args.output, [record for sample in range(args.samples)
                              for record in collect_student_actions(policy, episodes, registry, sample=sample)])


if __name__ == '__main__':
    main()
