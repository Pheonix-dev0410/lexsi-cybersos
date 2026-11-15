from dataclasses import dataclass
from pathlib import Path

from cybersos.policy import load_serving_contract
from cybersos.project_paths import SERVING_CONTRACT_PATH


@dataclass(frozen=True)
class ServingBudgets:
    """Action and token budgets frozen in the serving contract; training uses the same ones."""

    actions: int
    prompt_tokens: int
    context_tokens: int
    generation_tokens: int
    sequence_tokens: int


def load_serving_budgets(path: str | Path = SERVING_CONTRACT_PATH) -> ServingBudgets:
    return ServingBudgets(**load_serving_contract(path).fields['budgets'])
