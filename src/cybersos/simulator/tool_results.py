import json
from collections.abc import Mapping
from dataclasses import dataclass

from cybersos.domain import ToolName
from cybersos.domain.frozen_values import freeze
from cybersos.serialization import to_json_value


@dataclass(frozen=True)
class ToolResult:
    tool_name: ToolName
    ok: bool
    data: Mapping[str, object]
    error: str | None = None
    paused: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, 'data', freeze(dict(self.data)))


def render_tool_result(result: ToolResult) -> str:
    return json.dumps({'tool_name': result.tool_name.value, 'ok': result.ok,
                       'data': to_json_value(result.data), 'error': result.error,
                       'paused': result.paused}, sort_keys=True)
