from cybersos.data.serving_budgets import ServingBudgets
from cybersos.policy import ChatTokenizer, PromptBudgetExceeded


def split_token_ids(prompt: str, completion: str, tokenizer: ChatTokenizer,
                    budgets: ServingBudgets) -> tuple[list[int], list[int]]:
    """Token IDs of one rendered decision, refusing truncation or a merged boundary token.

    Training labels mask the prompt by position, so the concatenation must tokenize as
    exactly the prompt tokens followed by the completion tokens, within the model context.
    """
    prompt_ids = tokenizer.encode(prompt, add_special_tokens=False)
    completion_ids = tokenizer.encode(completion, add_special_tokens=False)
    sequence_ids = tokenizer.encode(prompt + completion, add_special_tokens=False)
    if (len(prompt_ids) > budgets.prompt_tokens or len(completion_ids) > budgets.generation_tokens
            or len(sequence_ids) > budgets.context_tokens):
        raise PromptBudgetExceeded('Rendered decision exceeds a token budget; no truncation')
    if not completion_ids or sequence_ids != prompt_ids + completion_ids:
        raise ValueError('token_boundary_mismatch')
    return prompt_ids, completion_ids
