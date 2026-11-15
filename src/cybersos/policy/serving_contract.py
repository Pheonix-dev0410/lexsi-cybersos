from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cybersos.domain.frozen_values import freeze
from cybersos.policy.contract_validation import RULE_CORPORA, validate_contract
from cybersos.policy.prompt_templates import (
    POLICY, PROMPT_VERSION, SERIALIZATION_VERSION, TOOLS_FALLBACK_PROMPT, TOOL_RESULT_FORMAT,
)
from cybersos.policy.tool_descriptions import render_tool_descriptions
from cybersos.project_paths import PROJECT_ROOT, SERVING_CONTRACT_PATH
from cybersos.serialization import canonical_json_sha256, file_sha256, load_strict_yaml, to_json_value


def contract_hash(fields: Mapping[str, Any]) -> str:
    return canonical_json_sha256(fields)


@dataclass(frozen=True)
class ServingContract:
    fields: Mapping[str, Any]

    def __post_init__(self) -> None:
        data = to_json_value(self.fields)
        validate_contract(data)
        object.__setattr__(self, 'fields', freeze(data))

    @property
    def contract_hash(self) -> str:
        return contract_hash(self.fields)

    @property
    def end_of_turn_token(self) -> str:
        """The token that ends the policy's response: generation stops there and SFT targets end with it."""
        return self.fields['serialization']['end_of_turn_token']

    def output_key(self, identity: Mapping[str, Any], *, case_id: str) -> str:
        return contract_hash({'contract_hash': self.contract_hash,
                              'model_identity': dict(identity), 'case_id': case_id})

    def validate_implementation(self, *, root: str | Path = PROJECT_ROOT,
                                require_resolved: bool = False) -> None:
        data = to_json_value(self.fields)
        validate_contract(data, require_resolved=require_resolved)
        expected = {'version': PROMPT_VERSION, 'policy': POLICY,
                    'tools_fallback': TOOLS_FALLBACK_PROMPT, 'tool_result': TOOL_RESULT_FORMAT,
                    'examples': []}
        if data['prompt'] != expected or data['serialization']['version'] != SERIALIZATION_VERSION:
            raise ValueError('Prompt/serialization implementation differs from frozen contract')
        if (data['tools']['definitions_text'] != render_tool_descriptions() or
                data['observations']['renderer_version'] != SERIALIZATION_VERSION):
            raise ValueError('Tool descriptions or observation renderer differ from contract')
        root = Path(root)
        for name in RULE_CORPORA:
            if file_sha256(root / data['rules'][f'{name}_path']) != data['rules'][f'{name}_sha256']:
                raise ValueError(f'Frozen rule corpus changed: {name}')
        for path, digest in data['guard']['files_sha256'].items():
            if file_sha256(root / path) != digest:
                raise ValueError(f'Frozen guard implementation changed: {path}')


def load_serving_contract(path: str | Path = SERVING_CONTRACT_PATH, *,
                          require_resolved: bool = False) -> ServingContract:
    path = Path(path)
    data = load_strict_yaml(path)
    if not isinstance(data, dict):
        raise ValueError('Serving contract must be a mapping')
    result = ServingContract(data)
    result.validate_implementation(root=path.resolve().parent.parent, require_resolved=require_resolved)
    return result
