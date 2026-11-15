import ast
import inspect
import json
import re
from typing import Any

from cybersos.training.rollout_patch import PATCH_PATH, VENDOR_PATH, patched_rollout_source
from rollout_fixtures import TestStep, TestTrajectory, load_pinned_tool_parser


CONTROL_FUNCTIONS = {'_execute_trajectory', '_extract_tool_calls', '_normalise_tool_calls',
                     '_load_first_json_object', '_extract_balanced_json_object', '_build_tool_schema',
                     '_fallback_tool_schema', '_get_callable'}


def load_cpu_rollout_control() -> Any:
    """Execute the patched AgentTune control loop on CPU, without its heavy imports."""
    tree = ast.parse(patched_rollout_source(VENDOR_PATH, PATCH_PATH))
    nodes: list[ast.stmt] = [
        ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)]
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in CONTROL_FUNCTIONS:
            nodes.append(node)
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and
                isinstance(node.value.func, ast.Attribute) and
                isinstance(node.value.func.value, ast.Name) and node.value.func.value.id == 're'):
            nodes.append(node)
    namespace = dict(vars(load_pinned_tool_parser())) | {
        'json': json, 're': re, 'inspect': inspect, 'Step': TestStep, 'Trajectory': TestTrajectory,
        'DEFAULT_TOOL_RESULT_FORMAT': '{name}: {content}', 'DEFAULT_TOOLS_FALLBACK_PROMPT': '{tools}',
    }
    compiled = ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))
    exec(compile(compiled, str(PATCH_PATH), 'exec'), namespace)
    return namespace['_execute_trajectory']
