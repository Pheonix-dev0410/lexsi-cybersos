import pytest

from cybersos.domain import Action, ToolName
from cybersos.safety import parse_action


@pytest.mark.parametrize('raw', [
    '{}', '[]', '[{}, {}]', 'not json', '```json\n[]\n```',
    '[{"tool_name":"unknown","parameters":{}}]',
    '[{"tool_name":"ask_access","parameters":{},"extra":1}]',
    '[{"tool_name":"ask_access","parameters":[]}]',
    '[{"tool_name":"ask_access","parameters":{},"tool_name":"finish"}]',
    '[{"tool_name":"ask_access","parameters":{"field":NaN}}]',
    '[{"tool_name":"ask_access"}]',
])
def test_rejects_non_contract_outputs(raw: str) -> None:
    parsed = parse_action(raw)
    assert parsed.action is None
    assert parsed.error
    assert parsed.raw_text == raw


def test_serialized_action_parses_back_to_itself() -> None:
    action = Action(ToolName.ASK_ACCESS, {'field': 'backup_code_accessible_now'})
    assert parse_action(action.to_json()).action == action
