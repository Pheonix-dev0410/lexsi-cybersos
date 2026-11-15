import gc
from dataclasses import asdict
from typing import Any

from cybersos.data.serving_budgets import load_serving_budgets
from cybersos.policy import load_serving_contract
from cybersos.serialization import read_jsonl, write_json
from cybersos.training.adapter_checks import (
    adapter_configuration, model_configuration, reload_in_fresh_process, require_cuda,
    require_new_output_dir, snapshot_trainable_adapter, verify_adapter_update,
)
from cybersos.training.development_evaluation import load_development_inputs, run_development_smoke
from cybersos.training.model_identity_checks import ADAPTER_METADATA, base_identity
from cybersos.training.sft_config import SFTConfig
from cybersos.training.sft_data_checks import inspect_rendered_training_file, verify_trainer_labels


def train_sft(config: SFTConfig, *, smoke: bool = False) -> dict[str, Any]:
    identity = base_identity(config.path('base_manifest_path'), config.path('model_path'))
    budgets = load_serving_budgets(config.path('serving_contract_path'))
    development = (load_development_inputs(config.path('serving_contract_path'),
                                           config.path('development_scenarios_path'))
                   if smoke else None)
    require_cuda(config.precision)
    destination = require_new_output_dir(config.path('output_dir'))
    from aligntune.core.backend_factory import create_sft_trainer

    trainer = create_sft_trainer(**config.factory_arguments(budgets, smoke=smoke))
    trainer.setup_model()
    tokenizer, model = trainer.tokenizer, trainer.model
    # The rendered prompt already carries the template's BOS, and TRL tokenizes with special
    # tokens on: without this it trains on a doubled BOS and appends its own EOS after the
    # contract's end-of-response token. The label check below proves the sequences match.
    tokenizer.add_bos_token = False
    tokenizer.eos_token = load_serving_contract(config.path('serving_contract_path')).end_of_turn_token
    dataset = config.path('rendered_dataset_path')
    inspected = inspect_rendered_training_file(dataset, tokenizer, budgets)
    before = snapshot_trainable_adapter(model)
    write_json(destination / 'resolved_sft_config.json', asdict(config) | {'smoke': smoke})
    write_json(destination / 'label_inspection.json', inspected)
    result = trainer.train()
    # AlignTune builds the TRL trainer inside train(), so its real collator is checked afterwards;
    # a mismatch leaves no adapter metadata, which every later stage requires.
    verify_trainer_labels(trainer.trainer, inspected, destination / 'actual_trl_labels.json')
    largest_update = verify_adapter_update(model, before, float(result['final_loss']))
    for adapter in model.peft_config.values():
        adapter.revision = identity['base_revision']
    model.save_pretrained(str(destination))
    tokenizer.save_pretrained(str(destination))
    metadata = identity | {
        'torch_dtype': 'bfloat16' if config.precision == 'bf16' else 'float16',
        'smoke_prefix': read_jsonl(dataset)[0]['instruction'],
        'generation_tokens': budgets.generation_tokens,
        'model_configuration': model_configuration(model),
        'adapter_configuration': adapter_configuration(model),
        'trainable_parameters': sum(value.numel() for value in before.values()),
        'trainable_modules': sorted(before), 'largest_adapter_update': largest_update,
        'smoke': smoke,
    }
    write_json(destination / ADAPTER_METADATA, metadata)
    summary = result | {'largest_adapter_update': largest_update, 'smoke': smoke}
    if development is not None:
        import torch

        del before, model, trainer
        gc.collect()
        torch.cuda.empty_cache()
        digest = reload_in_fresh_process(destination)
        summary['development'] = run_development_smoke(
            development, destination, digest, base_manifest=config.path('base_manifest_path'),
            label='sft')
    return summary
