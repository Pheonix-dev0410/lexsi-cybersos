import re
from collections.abc import Mapping
from math import isfinite
from typing import Any

from cybersos.policy.model_identity import require_immutable_revision


RULE_CORPORA = ('playbooks', 'sources')
_SHA256 = re.compile(r'[0-9a-f]{64}')

_SHAPE = {
    'base_model': {'model_id', 'revision', 'adapter_hash'},
    'tokenizer': {'model_id', 'revision', 'chat_template_sha256'},
    'inference_runtime': {'framework', 'transformers_version', 'torch_version'},
    'prompt': {'version', 'policy', 'tools_fallback', 'tool_result', 'examples'},
    'serialization': {'version', 'canonical_roles', 'native_tools', 'template_applications',
                      'generation_boundary', 'end_of_turn_token', 'completion_only_loss',
                      'assistant_only_loss'},
    'tools': {'definitions_text'},
    'rules': {'playbooks_path', 'playbooks_sha256', 'sources_path', 'sources_sha256',
              'retrieval', 'valid_action_filter'},
    'observations': {'mode', 'renderer_version', 'history', 'facts', 'retrieved_context'},
    'guard': {'version', 'files_sha256'},
    'budgets': {'actions', 'prompt_tokens', 'context_tokens', 'generation_tokens', 'sequence_tokens'},
    'numerics': {'precision', 'quantization', 'device'},
    'decoding': {'do_sample', 'num_beams', 'temperature', 'top_p', 'use_cache'},
    'failure_policy': {'malformed_output', 'retries', 'timeout_seconds', 'timeout_outcome',
                       'raw_proposals', 'overflow'},
    'cost_accounting': {'input_tokens', 'output_tokens', 'blocked_proposals', 'failed_episodes'},
}

_FIXED_SETTINGS = {
    ('observations', 'mode'): 'structured', ('observations', 'history'): 'observed_tool_results_as_compact_calls',
    ('observations', 'facts'): 'all_observed_with_provenance_and_corrections',
    ('observations', 'retrieved_context'):
        'retrieved_rule_prerequisites_and_sources_without_simulator_effects',
    ('rules', 'retrieval'): 'explicit_lookup_only', ('rules', 'valid_action_filter'): False,
    ('serialization', 'native_tools'): False, ('serialization', 'template_applications'): 1,
    ('serialization', 'generation_boundary'): True,
    ('serialization', 'completion_only_loss'): True, ('serialization', 'assistant_only_loss'): False,
    ('failure_policy', 'malformed_output'): 'block_and_count_action_no_repair',
    ('failure_policy', 'retries'): 0, ('failure_policy', 'overflow'): 'reject_without_truncation',
    ('failure_policy', 'raw_proposals'): 'log_before_guard',
    ('failure_policy', 'timeout_outcome'): 'timeout',
    ('inference_runtime', 'framework'): 'transformers', ('numerics', 'quantization'): 'none',
    ('decoding', 'do_sample'): False, ('decoding', 'num_beams'): 1,
    ('decoding', 'temperature'): None, ('decoding', 'top_p'): None,
    ('decoding', 'use_cache'): True,
}


def validate_contract(data: Mapping[str, Any], *, require_resolved: bool = False) -> None:
    _validate_shape(data)
    _validate_budgets(data['budgets'])
    _validate_settings(data)
    _validate_identities(data)
    _validate_digests(data)
    if require_resolved:
        _validate_resolved(data)


def _validate_shape(data: Mapping[str, Any]) -> None:
    if set(data) != set(_SHAPE) | {'contract_version'} or data['contract_version'] != 'cybersos-serving-v1':
        raise ValueError('Unknown serving contract version or fields')
    for section, keys in _SHAPE.items():
        if not isinstance(data[section], Mapping) or set(data[section]) != keys:
            raise ValueError(f'Missing or extra serving contract fields: {section}')


def _validate_budgets(budgets: Mapping[str, Any]) -> None:
    for key, value in budgets.items():
        if type(value) is not int or value < 1:
            raise ValueError(f'Invalid budget: {key}')
    if (budgets['actions'] > 12 or budgets['prompt_tokens'] + budgets['generation_tokens'] >
            budgets['context_tokens'] or budgets['sequence_tokens'] < budgets['context_tokens']):
        raise ValueError('Inconsistent action, prompt, context, or sequence budgets')


def _validate_settings(data: Mapping[str, Any]) -> None:
    for (section, key), value in _FIXED_SETTINGS.items():
        actual = data[section][key]
        if actual != value or type(actual) is not type(value):
            raise ValueError(f'Unsupported serving setting: {section}.{key}')
    if data['serialization']['canonical_roles'] != ['system', 'user', 'assistant']:
        raise ValueError('Canonical roles must be plain role/content messages')
    if data['prompt']['examples'] != []:
        raise ValueError('This prompt version has no few-shot examples')
    if data['numerics']['precision'] not in {'float32', 'float16', 'bfloat16'}:
        raise ValueError('Unsupported precision')
    timeout = data['failure_policy']['timeout_seconds']
    if type(timeout) not in {int, float} or not isfinite(timeout) or timeout <= 0:
        raise ValueError('Timeout must be positive')
    if any(value is not True for value in data['cost_accounting'].values()):
        raise ValueError('Cost accounting must include all proposals and failures')


def _validate_identities(data: Mapping[str, Any]) -> None:
    if not _nonempty_text(data['serialization']['end_of_turn_token']):
        raise ValueError('Missing end-of-turn token')
    for section in ('base_model', 'tokenizer'):
        if not _nonempty_text(data[section]['model_id']):
            raise ValueError('Missing model identity')
        if not _nonempty_text(data[section]['revision']):
            raise ValueError('Missing base/tokenizer revision')
    if not _nonempty_text(data['numerics']['device']):
        raise ValueError('Missing inference device')


def _validate_digests(data: Mapping[str, Any]) -> None:
    adapter = data['base_model']['adapter_hash']
    if adapter is not None and not _is_sha256(adapter):
        raise ValueError('Invalid frozen adapter SHA256')
    guards = data['guard']['files_sha256']
    if not isinstance(guards, Mapping) or not guards:
        raise ValueError('Missing guard source hashes')
    digests = [data['rules'][f'{name}_sha256'] for name in RULE_CORPORA] + list(guards.values())
    if not all(_is_sha256(digest) for digest in digests):
        raise ValueError('Invalid rule/guard source SHA256')


def _validate_resolved(data: Mapping[str, Any]) -> None:
    for section in ('base_model', 'tokenizer'):
        require_immutable_revision(data[section]['revision'])
    if data['base_model']['revision'] != data['tokenizer']['revision']:
        raise ValueError('Tokenizer and base revisions differ')
    if data['base_model']['model_id'] != data['tokenizer']['model_id']:
        raise ValueError('Tokenizer and base identities differ')
    if not _is_sha256(data['tokenizer']['chat_template_sha256']):
        raise ValueError('Resolve the tokenizer chat-template SHA256 before a run')
    for key in ('transformers_version', 'torch_version'):
        value = data['inference_runtime'][key]
        if not isinstance(value, str) or not re.fullmatch(r'\d+\.\d+.*', value):
            raise ValueError(f'Resolve the inference runtime version: {key}')


def _nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None
