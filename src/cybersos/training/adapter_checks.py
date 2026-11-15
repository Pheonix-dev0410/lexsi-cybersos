import math
import subprocess
import sys
from pathlib import Path
from typing import Any

from cybersos.policy.model_identity import adapter_hash


def model_configuration(model: Any) -> dict[str, Any]:
    fields = ('model_type', 'architectures', 'vocab_size', 'hidden_size', 'intermediate_size',
              'num_hidden_layers', 'num_attention_heads', 'num_key_value_heads', 'head_dim',
              'max_position_embeddings', 'tie_word_embeddings', 'rope_scaling', 'rope_theta',
              'hidden_act', 'layer_norm_eps', 'rms_norm_eps', 'is_encoder_decoder')
    values = model.config.to_dict()
    return {field: values[field] for field in fields if field in values}


def adapter_configuration(model: Any) -> dict[str, Any]:
    adapter = model.peft_config['default']
    return {'revision': adapter.revision, 'r': adapter.r, 'lora_alpha': adapter.lora_alpha,
            'lora_dropout': adapter.lora_dropout,
            'target_modules': (sorted(adapter.target_modules) if not isinstance(adapter.target_modules, str)
                               else adapter.target_modules)}


def require_cuda(precision: str) -> None:
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError('Training requires the validated CUDA environment; unavailable on this machine')
    if precision == 'bf16' and not torch.cuda.is_bf16_supported():
        raise RuntimeError('BF16 is unavailable; validate and explicitly configure FP16')


def snapshot_trainable_adapter(model: Any) -> dict[str, Any]:
    trainable = {name: value.detach().cpu().clone() for name, value in model.named_parameters()
                 if value.requires_grad}
    if not trainable or not sum(value.numel() for value in trainable.values()):
        raise RuntimeError('No trainable adapter parameters')
    if any('lora_' not in name for name in trainable):
        raise RuntimeError('Unexpected trainable base parameters; expected only LoRA')
    return trainable


def verify_adapter_update(model: Any, before: dict[str, Any], loss: float) -> float:
    import torch

    if not math.isfinite(loss):
        raise RuntimeError('Training loss is not finite')
    after = dict(model.named_parameters())
    differences = [after[name].detach().cpu().float() - old.float() for name, old in before.items()]
    if any(not bool(torch.isfinite(delta).all()) for delta in differences):
        raise RuntimeError('Adapter update contains nonfinite values')
    largest = max(float(delta.abs().max()) for delta in differences)
    if largest <= 0:
        raise RuntimeError('Adapter weights did not change')
    return largest


def require_new_output_dir(path: str | Path) -> Path:
    """Refuse to write into a nonempty directory so earlier adapters stay immutable."""
    destination = Path(path)
    if destination.exists() and any(destination.iterdir()):
        raise ValueError(f'Use a new output directory to preserve earlier adapters: {destination}')
    return destination


def reload_in_fresh_process(adapter_path: str | Path) -> str:
    """Reload and smoke-generate in a new interpreter; return the hash of what was checked."""
    digest = adapter_hash(adapter_path)
    subprocess.run([sys.executable, '-m', 'cybersos.training.reload_adapter',
                    str(Path(adapter_path).resolve())], check=True)
    if adapter_hash(adapter_path) != digest:
        raise RuntimeError('Adapter files changed during the fresh-process reload check')
    return digest
