import gc
from dataclasses import asdict
from typing import Any

from cybersos.data.serving_budgets import load_serving_budgets
from cybersos.playbooks import load_project_registry
from cybersos.policy.model_identity import adapter_hash
from cybersos.serialization import to_json_value, write_json, write_jsonl
from cybersos.training.adapter_checks import (
    adapter_configuration, model_configuration, reload_in_fresh_process, require_cuda,
    require_new_output_dir, snapshot_trainable_adapter, verify_adapter_update,
)
from cybersos.training.agent_config import AgentConfig
from cybersos.training.agenttune_bridge import AgentTuneBridge
from cybersos.training.development_evaluation import load_development_inputs, run_development_smoke
from cybersos.training.model_identity_checks import ADAPTER_METADATA, read_adapter_metadata
from cybersos.training.residual_target_gate import require_residual_target
from cybersos.training.rollout_patch import AGENTTUNE_COMMIT, check_rollout_patch
from cybersos.training.scenario_store import (
    ScenarioStore, load_training_scenarios, select_pilot_scenarios,
)
from cybersos.training.trajectory_contexts import CONTEXT_VERSION
from cybersos.training.trajectory_forward import TrajectoryForward
from cybersos.training.trajectory_reward import FORMULA_ID


SMOKE_SCENARIOS = 2


def train_agent(config: AgentConfig, *, smoke: bool = False) -> dict[str, Any]:
    target = require_residual_target(config.path('residuals_path'))
    patch_hash = check_rollout_patch(config.path('vendor_path'), config.path('patch_path'))
    sft_path = config.path('sft_adapter_path')
    sft_hash = adapter_hash(sft_path)
    metadata = read_adapter_metadata(sft_path)
    budgets = load_serving_budgets(config.path('serving_contract_path'))
    development = (load_development_inputs(config.path('serving_contract_path'),
                                           config.path('development_scenarios_path'))
                   if smoke else None)
    destination = require_new_output_dir(config.path('output_dir'))
    require_cuda(config.precision)
    import torch
    from agenttune.core.backend_factory import create_agentic_trainer
    from datasets import Dataset
    from peft import AutoPeftModelForCausalLM
    from transformers import AutoTokenizer

    torch.manual_seed(config.seed)
    student = AutoPeftModelForCausalLM.from_pretrained(
        sft_path, is_trainable=True, local_files_only=True,
        torch_dtype=torch.bfloat16 if config.precision == 'bf16' else torch.float16)
    tokenizer = AutoTokenizer.from_pretrained(sft_path, local_files_only=True)
    if (model_configuration(student) != metadata['model_configuration'] or
            adapter_configuration(student) != metadata['adapter_configuration']):
        raise ValueError('Warm-started adapter differs from the saved SFT configuration')
    before = snapshot_trainable_adapter(student)
    pilot = select_pilot_scenarios(load_training_scenarios(config.path('scenarios_path')),
                                   SMOKE_SCENARIOS if smoke else config.pilot_scenarios,
                                   seed=config.seed)
    store = ScenarioStore(pilot, load_project_registry(), tokenizer, budgets, seed=config.seed)
    write_jsonl(destination / 'budget_exhausted_scenarios.jsonl', store.excluded)
    bridge = AgentTuneBridge(store, config, forward=TrajectoryForward(student))
    write_json(destination / 'resolved_agent_config.json', asdict(config) | {
        'smoke': smoke, 'target': target, 'sft_adapter_hash': sft_hash, 'budgets': budgets,
        'pilot_scenario_ids': [scenario.scenario_id for scenario in pilot],
        'agenttune_commit': AGENTTUNE_COMMIT, 'patch_sha256': patch_hash, 'formula_id': FORMULA_ID,
        'context_version': CONTEXT_VERSION})
    trainer = create_agentic_trainer(
        **config.factory_arguments(budgets, smoke=smoke), model=student, processing_class=tokenizer,
        train_dataset=Dataset.from_list(store.rows), rollout_func=bridge.rollout,
        reward_funcs=[bridge.reward])
    result = trainer.train()
    losses = [float(item['loss']) for item in trainer.trainer.state.log_history if 'loss' in item]
    if not losses:
        raise RuntimeError('Agent training did not report an optimizer loss')
    update = verify_adapter_update(student, before, losses[-1])
    if trainer.trainer.state.global_step < (1 if smoke else config.max_steps):
        raise RuntimeError('Agent training stopped before the requested optimizer updates')
    if not (destination / 'reward_variance.jsonl').is_file():
        raise RuntimeError('No trajectory reward variance was logged; training bridge is invalid')
    student.save_pretrained(str(destination))
    tokenizer.save_pretrained(str(destination))
    write_json(destination / ADAPTER_METADATA, metadata | {
        'smoke': smoke, 'parent_sft_hash': sft_hash, 'formula_id': FORMULA_ID,
        'largest_adapter_update': update, 'patch_sha256': patch_hash, 'context_version': CONTEXT_VERSION})
    summary = {'training': to_json_value(result), 'largest_adapter_update': update, 'target': target}
    if development is not None:
        del before, student, trainer, bridge
        gc.collect()
        torch.cuda.empty_cache()
        digest = reload_in_fresh_process(destination)
        summary['development'] = run_development_smoke(
            development, destination, digest, base_manifest=config.path('base_manifest_path'),
            label='agent')
    return summary
