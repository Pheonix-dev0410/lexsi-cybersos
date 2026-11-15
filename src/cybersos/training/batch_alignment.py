from typing import Any


ALIGNED_FIELDS = frozenset({'prompt_ids', 'completion_ids', 'logprobs', 'env_mask',
                            'trajectories', 'conversations'})


def normalize_batch(prompts: Any) -> list[Any]:
    if isinstance(prompts, dict):
        return [prompts]
    if not isinstance(prompts, list):
        raise ValueError('Expected canonical conversations or a list of prompt occurrences')
    if prompts and isinstance(prompts[0], dict) and 'role' in prompts[0]:
        return [prompts]
    return prompts


def concatenate_aligned_batch_fields(outputs: list[dict[str, Any]]) -> dict[str, Any]:
    if not outputs:
        raise ValueError('Cannot concatenate an empty rollout batch')
    keys = set(outputs[0])
    if not ALIGNED_FIELDS <= keys or any(set(output) != keys for output in outputs):
        raise ValueError('Rollout batch fields differ or required fields are missing')
    merged: dict[str, Any] = {}
    for output in outputs:
        count = len(output['trajectories'])
        if count != 1:
            raise ValueError('Each isolated invocation must return exactly one trajectory')
        for name, value in output.items():
            if name in ALIGNED_FIELDS or isinstance(value, list):
                if not isinstance(value, list) or len(value) != count:
                    raise ValueError(f'Misaligned batch field: {name}')
                merged.setdefault(name, []).extend(value)
            elif name == 'tools_used' and isinstance(value, bool):
                merged[name] = merged.get(name, False) or value
            elif name in merged and merged[name] != value:
                raise ValueError(f'Inconsistent scalar rollout field: {name}')
            else:
                merged[name] = value
        for index in range(count):
            lengths = {len(output[name][index]) for name in ('completion_ids', 'logprobs', 'env_mask')}
            if len(lengths) != 1:
                raise ValueError('Completion tokens, logprobs, and environment masks must align')
    return merged
