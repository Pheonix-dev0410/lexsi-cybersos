from collections.abc import Sequence
from pathlib import Path

from cybersos.evaluation.run_manifest import output_cache_key
from cybersos.policy import ServingContract
from cybersos.serialization import canonical_json_sha256, file_sha256, files_sha256

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def package_sources_sha256(package: str) -> str:
    return files_sha256((PACKAGE_ROOT / package).glob('*.py'))


def rule_baseline_checkpoint() -> str:
    """Q and R have no weights; their checkpoint is the source of the rule policies."""
    return package_sources_sha256('baselines')


def version_hashes(contract: ServingContract, *, cases_path: Path, split: str,
                   episode_ids: Sequence[str], config_path: Path) -> dict[str, str]:
    """Every input a run's outputs depend on, recorded in its manifest and folded into its cache key."""
    fields = contract.fields
    return {'data': file_sha256(cases_path),
            'split': canonical_json_sha256({'split': split, 'episode_ids': sorted(episode_ids)}),
            'source_corpus': canonical_json_sha256(fields['rules']),
            'prompt': canonical_json_sha256(fields['prompt']),
            'tools': canonical_json_sha256(fields['tools']),
            'guard': canonical_json_sha256(fields['guard']),
            'simulator': package_sources_sha256('simulator'),
            'runtime': package_sources_sha256('runtime'),
            'orchestration': package_sources_sha256('evaluation'),
            'eval_config': file_sha256(config_path),
            'serving_contract': contract.contract_hash}


def run_key(hashes: dict[str, str], contract: ServingContract, *, checkpoint_hash: str, seed: int) -> str:
    fields = contract.fields
    return output_cache_key(
        checkpoint_hash=checkpoint_hash, prompt_version=hashes['prompt'], tool_version=hashes['tools'],
        source_version=hashes['source_corpus'], guard_version=hashes['guard'],
        runtime_version=canonical_json_sha256([hashes[name] for name in
                                               ('simulator', 'runtime', 'orchestration', 'eval_config')]),
        scenario_revision=canonical_json_sha256([hashes['data'], hashes['split']]),
        observation_revision=canonical_json_sha256(fields['observations']),
        observation_mode=fields['observations']['mode'], decoding=dict(fields['decoding']), seed=seed)
