from cybersos.domain import AccessField, Action, Incident, Provider, TerminalState, ToolName


SCHEMAS = {
    ToolName.ASK_ACCESS: ({'field'}, set()),
    ToolName.LOOKUP_PLAYBOOK: ({'provider', 'incident'}, {'rule_id'}),
    ToolName.CHECK_STEP: ({'step_id'}, set()),
    ToolName.SIMULATE_STEP: ({'step_id'}, {'confirmation'}),
    ToolName.FINISH: ({'status', 'next_step_id', 'source_ids'}, set()),
}


def schema_error(action: Action) -> str | None:
    required, optional = SCHEMAS[action.tool_name]
    params = action.parameters
    if not required <= params.keys() or not params.keys() <= required | optional:
        return 'Missing or extra tool parameters'
    try:
        if action.tool_name == ToolName.ASK_ACCESS:
            AccessField(params['field'])
        elif action.tool_name == ToolName.LOOKUP_PLAYBOOK:
            Provider(params['provider'])
            Incident(params['incident'])
            if 'rule_id' in params and not isinstance(params['rule_id'], str):
                return 'rule_id must be a string'
        elif action.tool_name in {ToolName.CHECK_STEP, ToolName.SIMULATE_STEP}:
            if not isinstance(params['step_id'], str):
                return 'step_id must be a string'
            if 'confirmation' in params and not isinstance(params['confirmation'], bool):
                return 'confirmation must be boolean'
        else:
            TerminalState(params['status'])
            if params['next_step_id'] is not None and not isinstance(params['next_step_id'], str):
                return 'next_step_id must be a string or null'
            if not isinstance(params['source_ids'], (list, tuple)) or not all(
                    isinstance(source, str) for source in params['source_ids']):
                return 'source_ids must be a list of strings'
    except (ValueError, TypeError):
        return 'Unknown enum value or invalid parameter type'
    return None
