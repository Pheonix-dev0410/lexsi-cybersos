import json
from collections.abc import Mapping

from cybersos.domain import AccessField, ToolName
from cybersos.domain.access import normalize_value
from cybersos.domain.sensitive_text import replace_urls
from cybersos.policy.prompt_templates import TOOL_RESULT_FORMAT
from cybersos.simulator import ActionObservation, ToolResult


_TEXT_FIELDS = {
    ToolName.ASK_ACCESS: ('field', 'value', 'awaiting'),
    ToolName.CHECK_STEP: ('step_id', 'status'),
    ToolName.SIMULATE_STEP: ('step_id', 'instruction', 'scope_note', 'provider_response',
                             'evidence_basis', 'awaiting', 'reported_response'),
    ToolName.FINISH: ('terminal_state',),
    ToolName.LOOKUP_PLAYBOOK: (),
}
_RULE_TEXT = ('step_id', 'instruction', 'scope_note', 'checked_on', 'risk_level', 'review_status')
_APPLICATION_TEXT = ('instruction', 'scope_note', 'urls', 'source_ids')


def _text_fields(data: Mapping[str, object], fields: tuple[str, ...]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key in fields:
        if key in data:
            if not isinstance(data[key], str):
                raise ValueError(f'Expected observed text: {key}')
            result[key] = data[key]
    return result


def _string_list(value: object) -> list[str]:
    if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) for item in value):
        raise ValueError('Expected observed string sequence')
    return list(value)


def _rule(rule: object) -> dict[str, object]:
    if not isinstance(rule, Mapping):
        raise ValueError('Expected retrieved rule mapping')
    result = _text_fields(rule, _RULE_TEXT)
    for key in ('source_ids', 'urls'):
        if key in rule:
            result[key] = _string_list(rule[key])
    requires = rule.get('requires', {})
    if not isinstance(requires, Mapping):
        raise ValueError('Expected prerequisite mapping')
    result['requires'] = {AccessField(key).value: normalize_value(AccessField(key), value).value
                          for key, value in requires.items()}
    if 'unknown_requires_question' in rule:
        if type(rule['unknown_requires_question']) is not bool:
            raise ValueError('Expected question requirement boolean')
        result['unknown_requires_question'] = rule['unknown_requires_question']
    return result


def public_tool_result(result: ToolResult) -> ToolResult:
    """Project tool data through a closed schema before using the core serializer."""
    if type(result) is not ToolResult:
        raise TypeError('Expected a core ToolResult')
    if (type(result.ok) is not bool or type(result.paused) is not bool or
            (result.error is not None and not isinstance(result.error, str))):
        raise ValueError('Invalid tool-result envelope scalars')
    data = _text_fields(result.data, _TEXT_FIELDS[result.tool_name])
    if 'retryable' in result.data:
        if type(result.data['retryable']) is not bool:
            raise ValueError('Expected retryable boolean')
        data['retryable'] = result.data['retryable']
    for key in ('violations',):
        if key in result.data:
            data[key] = _string_list(result.data[key])
    if result.tool_name == ToolName.LOOKUP_PLAYBOOK:
        rules = result.data.get('rules', ())
        if not isinstance(rules, (list, tuple)):
            raise ValueError('Expected retrieved rule sequence')
        data['rules'] = [_rule(rule) for rule in rules]
    if result.tool_name == ToolName.CHECK_STEP:
        for key in ('blocked_fields', 'unknown_fields'):
            if key in result.data:
                data[key] = [AccessField(field).value for field in _string_list(result.data[key])]
        if 'revision' in result.data:
            if type(result.data['revision']) is not int:
                raise ValueError('Expected fact revision integer')
            data['revision'] = result.data['revision']
    if result.tool_name == ToolName.SIMULATE_STEP:
        for key in ('source_ids', 'urls'):
            if key in result.data:
                data[key] = _string_list(result.data[key])
    if result.tool_name == ToolName.FINISH and 'verified_access_restored' in result.data:
        if type(result.data['verified_access_restored']) is not bool:
            raise ValueError('Expected verified access boolean')
        data['verified_access_restored'] = result.data['verified_access_restored']
    return ToolResult(result.tool_name, result.ok, data, result.error, result.paused)


def _compact(value: object) -> str:
    if isinstance(value, (list, tuple)):
        return ', '.join(map(_compact, value)) or 'none'
    if isinstance(value, bool) or value is None:
        return json.dumps(value)
    return str(value)


def render_observed_tool_result(result: ToolResult) -> str:
    projected = public_tool_result(result)
    data = dict(projected.data)
    if result.tool_name == ToolName.LOOKUP_PLAYBOOK:
        data = {'retrieved_rules': f"{len(data.pop('rules', ()))} (listed under retrieved rules)"}
    if 'field' in data and 'value' in data:
        field = data.pop('field')
        data[str(field)] = data.pop('value')
    # The application shows instructions and official links; the policy needs only outcomes.
    for key in _APPLICATION_TEXT:
        data.pop(key, None)
    parts = [f'{key}={_compact(value)}' for key, value in sorted(data.items())]
    if not projected.ok:
        parts.insert(0, f'failed: {projected.error}' if projected.error else 'failed')
    if projected.paused:
        parts.append('paused for the person')
    return TOOL_RESULT_FORMAT.format(name=result.tool_name.value, content='; '.join(parts) or 'ok')


def render_action_observation(turn: ActionObservation) -> str:
    if type(turn) is not ActionObservation:
        raise TypeError('Expected a core ActionObservation')
    if turn.raw_proposal is not None and not isinstance(turn.raw_proposal, str):
        raise ValueError('Expected raw proposal text')
    # Echoed proposals are model text; a model-written destination must never reach a later prompt.
    if turn.action is not None:
        arguments = ', '.join(f'{key}={_compact(value)}' for key, value in sorted(turn.action.parameters.items()))
        action = replace_urls(f'{turn.action.tool_name.value}({arguments})')
    else:
        action = 'unparsed proposal ' + json.dumps(replace_urls(turn.raw_proposal or ''))
    lines = [action]
    if not turn.guard_verdict.allowed:
        violations = ', '.join(v.kind.value for v in turn.guard_verdict.violations) or 'unspecified'
        lines.append(f'guard blocked: {violations}')
    return '\n'.join(lines + [render_observed_tool_result(turn.result)])
