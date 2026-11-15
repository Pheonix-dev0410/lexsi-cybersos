from dataclasses import dataclass
from pathlib import Path

from cybersos.data.serving_budgets import ServingBudgets
from cybersos.project_paths import CONFIGS_DIR
from cybersos.training.config_loading import (
    load_typed_config, positive_integer, positive_rate, project_path, require_string,
)


PILOT_SCENARIO_RANGE = range(32, 65)
# AgentTune's rollout reserves this many context tokens below context_length for generation.
AGENTTUNE_CONTEXT_RESERVE = 256


@dataclass(frozen=True)
class AgentConfig:
    sft_adapter_path: str = 'runs/sft-adapter'
    output_dir: str = 'runs/agent-adapter'
    scenarios_path: str = 'data/scenarios/train.jsonl'
    residuals_path: str = 'reports/sft_residuals.md'
    patch_path: str = 'patches/agenttune_cybersos_rollout.patch'
    vendor_path: str = 'vendor/AgentTune'
    serving_contract_path: str = 'configs/baselines.yaml'
    base_manifest_path: str = 'configs/base_model.json'
    development_scenarios_path: str = 'data/scenarios/dev.jsonl'
    pilot_scenarios: int = 48
    max_steps: int = 20
    per_device_train_batch_size: int = 2
    gradient_accumulation_steps: int = 1
    num_generations: int = 2
    learning_rate: float = 1e-6
    precision: str = 'bf16'
    seed: int = 42

    def __post_init__(self) -> None:
        for name in ('sft_adapter_path', 'output_dir', 'scenarios_path', 'residuals_path',
                     'patch_path', 'vendor_path', 'serving_contract_path', 'base_manifest_path',
                     'development_scenarios_path'):
            require_string(name, getattr(self, name))
        for name in ('pilot_scenarios', 'max_steps', 'per_device_train_batch_size',
                     'gradient_accumulation_steps', 'num_generations'):
            positive_integer(name, getattr(self, name))
        positive_rate('learning_rate', self.learning_rate)
        if self.pilot_scenarios not in PILOT_SCENARIO_RANGE:
            raise ValueError('The agent pilot uses 32 to 64 training scenarios')
        if self.num_generations < 2 or self.per_device_train_batch_size % self.num_generations:
            raise ValueError('GRPO needs at least two samples and a divisible batch size')
        if self.precision not in {'bf16', 'fp16'} or type(self.seed) is not int:
            raise ValueError('Invalid precision or seed')

    def path(self, name: str) -> Path:
        return project_path(getattr(self, name))

    def factory_arguments(self, budgets: ServingBudgets, *, smoke: bool = False) -> dict[str, object]:
        if budgets.prompt_tokens > budgets.context_tokens - AGENTTUNE_CONTEXT_RESERVE:
            raise ValueError('Prompt budget leaves AgentTune no generation reserve')
        return {
            'algorithm': 'grpo', 'backend': 'trl', 'peft_config': None,
            'output_dir': str(self.path('output_dir')), 'max_steps': 1 if smoke else self.max_steps,
            'per_device_train_batch_size': self.per_device_train_batch_size,
            'gradient_accumulation_steps': self.gradient_accumulation_steps,
            'num_generations': self.num_generations, 'learning_rate': self.learning_rate,
            'max_completion_length': budgets.generation_tokens, 'use_vllm': False,
            'report_to': 'none', 'seed': self.seed, 'remove_unused_columns': False,
            'warmup_steps': 0, 'logging_steps': 1,
            'bf16': self.precision == 'bf16', 'fp16': self.precision == 'fp16',
        }


def load_agent_config(path: str | Path = CONFIGS_DIR / 'agent.yaml') -> AgentConfig:
    return load_typed_config(path, AgentConfig)
