import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from cybersos.domain.frozen_values import freeze
from cybersos.serialization import to_json_value


class ToolName(StrEnum):
    ASK_ACCESS = 'ask_access'
    LOOKUP_PLAYBOOK = 'lookup_playbook'
    CHECK_STEP = 'check_step'
    SIMULATE_STEP = 'simulate_step'
    FINISH = 'finish'


@dataclass(frozen=True)
class Action:
    tool_name: ToolName
    parameters: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, 'tool_name', ToolName(self.tool_name))
        object.__setattr__(self, 'parameters', freeze(dict(self.parameters)))

    def as_internal(self) -> dict[str, object]:
        return {'name': self.tool_name.value, 'arguments': to_json_value(self.parameters)}

    def to_json(self) -> str:
        return json.dumps([{'tool_name': self.tool_name.value,
                            'parameters': self.as_internal()['arguments']}], sort_keys=True)
