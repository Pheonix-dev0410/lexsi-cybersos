import json
from dataclasses import dataclass

from cybersos.domain import Action, ToolName


@dataclass(frozen=True)
class ParsedProposal:
    raw_text: str
    action: Action | None
    error: str | None = None


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON field')
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f'Non-JSON constant: {value}')


def parse_action(raw_text: str) -> ParsedProposal:
    try:
        value = json.loads(raw_text, object_pairs_hook=_unique_object,
                           parse_constant=_reject_constant)
        if not isinstance(value, list) or len(value) != 1:
            raise ValueError('Exactly one action in a JSON array is required')
        entry = value[0]
        if not isinstance(entry, dict) or set(entry) != {'tool_name', 'parameters'}:
            raise ValueError('Action requires only tool_name and parameters')
        if not isinstance(entry['parameters'], dict):
            raise ValueError('parameters must be an object')
        return ParsedProposal(raw_text, Action(ToolName(entry['tool_name']), entry['parameters']))
    except (ValueError, TypeError, RecursionError) as error:
        return ParsedProposal(raw_text, None, str(error))
