from cybersos.domain import AccessField, Incident, Provider, TerminalState, ToolName
from cybersos.playbooks import load_project_registry
from cybersos.safety.action_schema import SCHEMAS


_DESCRIPTIONS = {
    ToolName.ASK_ACCESS: 'Ask only whether an access factor is available; never collect its value.',
    ToolName.LOOKUP_PLAYBOOK: 'Retrieve source rules for the observed provider and incident.',
    ToolName.CHECK_STEP: 'Check a retrieved step against current observed prerequisites.',
    ToolName.SIMULATE_STEP: 'Attempt a supported step in simulation or present official guidance.',
    ToolName.FINISH: 'End with an evidence-supported outcome and source references.',
}
_PARAMETER_VALUES = {
    'field': ', '.join(field.value for field in AccessField),
    'provider': ', '.join(provider.value for provider in Provider),
    'incident': ', '.join(incident.value for incident in Incident),
    'status': ', '.join(state.value for state in TerminalState),
    'confirmation': 'true or false', 'step_id': 'a step id', 'rule_id': 'a step id',
    'next_step_id': 'a step id or null', 'source_ids': 'list of source ids',
}


def render_tool_descriptions() -> str:
    """Plain-text tool signatures generated from the action schema the guard enforces.

    Text signatures replace JSON Schema because the prompt budget is fixed and the schema
    repeated every enum inside nested objects; the permitted names and values are unchanged.
    """
    lines = []
    for tool, (required, optional) in SCHEMAS.items():
        names = sorted(required) + [f'{name}?' for name in sorted(optional)]
        lines.append(f'{tool.value}({", ".join(names)}): {_DESCRIPTIONS[tool]}')
        lines += [f'  {name}: {_PARAMETER_VALUES[name]}' for name in sorted(required | optional)]
    # Every reviewed id is listed, like the access-field enum: a closed vocabulary, never a list
    # filtered by the person's state. Without it the policy recalled near-miss ids from memory.
    registry = load_project_registry()
    lines.append(f'Step ids: {", ".join(registry.rules)}')
    lines.append(f'Source ids: {", ".join(registry.sources)}')
    return '\n'.join(lines)
