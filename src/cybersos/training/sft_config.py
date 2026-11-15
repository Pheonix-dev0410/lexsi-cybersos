from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from cybersos.data.serving_budgets import ServingBudgets
from cybersos.project_paths import CONFIGS_DIR
from cybersos.training.config_loading import (
    load_typed_config, positive_integer, positive_rate, project_path, require_string,
)


PATH_FIELDS = ('model_path', 'base_manifest_path', 'serving_contract_path',
               'development_scenarios_path', 'rendered_dataset_path', 'output_dir')


@dataclass(frozen=True)
class SFTConfig:
    model_path: str = 'artifacts/base'
    base_manifest_path: str = 'configs/base_model.json'
    serving_contract_path: str = 'configs/baselines.yaml'
    development_scenarios_path: str = 'data/scenarios/dev.jsonl'
    rendered_dataset_path: str = 'data/rendered/train_alpaca.jsonl'
    output_dir: str = 'runs/sft-adapter'
    num_epochs: int = 1
    batch_size: int = 1
    gradient_accumulation_steps: int = 8
    learning_rate: float = 1e-4
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    lora_target_modules: str = 'all-linear'
    gradient_checkpointing: bool = True
    precision: str = 'bf16'
    quantization: dict[str, Any] | None = None
    seed: int = 42

    def __post_init__(self) -> None:
        for name in (*PATH_FIELDS, 'lora_target_modules'):
            require_string(name, getattr(self, name))
        if Path(self.rendered_dataset_path).suffix != '.jsonl':
            raise ValueError('SFT requires a single rendered JSONL file')
        for name in ('num_epochs', 'batch_size', 'gradient_accumulation_steps', 'lora_r', 'lora_alpha'):
            positive_integer(name, getattr(self, name))
        positive_rate('learning_rate', self.learning_rate)
        if type(self.lora_dropout) not in (int, float) or not 0 <= self.lora_dropout < 1:
            raise ValueError('LoRA dropout must be in [0, 1)')
        if self.precision not in {'bf16', 'fp16'}:
            raise ValueError('Precision must be bf16 or a validated fp16 configuration')
        if type(self.seed) is not int or type(self.gradient_checkpointing) is not bool:
            raise ValueError('Invalid seed or gradient checkpointing setting')
        if self.quantization not in (None, {}):
            raise ValueError('Quantization requires a separate validated GPU smoke run; disabled initially')

    def path(self, name: str) -> Path:
        return project_path(getattr(self, name))

    def factory_arguments(self, budgets: ServingBudgets, *, smoke: bool = False) -> dict[str, Any]:
        values = {key: value for key, value in asdict(self).items() if key not in PATH_FIELDS}
        return values | {
            'model_name': str(self.path('model_path')),
            'dataset_name': str(self.path('rendered_dataset_path')),
            'output_dir': str(self.path('output_dir')), 'max_seq_length': budgets.context_tokens,
            'backend': 'trl', 'task_type': 'instruction_following', 'format_type': 'alpaca',
            'system_prompt': None, 'use_lora': True, 'completion_only_loss': True,
            'assistant_only_loss': False, 'packing': False, 'val_split_ratio': None,
            'test_split_ratio': None, 'load_best_model_at_end': False, 'eval_strategy': 'no',
            'loggers': [], 'report_to': 'none', 'quantization': self.quantization or {},
            'bf16': self.precision == 'bf16', 'fp16': self.precision == 'fp16',
            # Enough steps for the reload check to see the learned action format, not just a loadable file.
            **({'max_samples': 256, 'max_steps': 24} if smoke else {}),
        }


def load_sft_config(path: str | Path = CONFIGS_DIR / 'sft.yaml') -> SFTConfig:
    return load_typed_config(path, SFTConfig)
