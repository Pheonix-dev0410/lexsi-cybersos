from cybersos.domain import Action, FactSource, SessionMode, ToolName
from cybersos.simulator.episode_state import EpisodeState
from cybersos.simulator.tool_results import ToolResult


def temporary_failure(state: EpisodeState, action: Action) -> ToolResult | None:
    if state.mode != SessionMode.BENCHMARK:
        return None
    for index, failure in enumerate(state.scenario.temporary_tool_failures):
        if (index not in state.failed_once and action.tool_name == failure.tool_name and
                (failure.step_id is None or action.parameters.get('step_id') == failure.step_id)):
            state.failed_once.add(index)
            data = {'retryable': True}
            if 'step_id' in action.parameters:
                data['step_id'] = action.parameters['step_id']
            state.log('temporary_tool_failure', {'tool_name': action.tool_name.value, **data})
            return ToolResult(action.tool_name, False, data, 'temporary_tool_failure')
    return None


def apply_corrections(state: EpisodeState, action: Action, result: ToolResult) -> None:
    if state.mode != SessionMode.BENCHMARK:
        return
    for index, correction in enumerate(state.scenario.corrections):
        if index in state.applied_corrections:
            continue
        question = (result.ok and action.tool_name == ToolName.ASK_ACCESS and
                    correction.after_question is not None and
                    action.parameters['field'] == correction.after_question)
        step = (action.tool_name == ToolName.SIMULATE_STEP and
                correction.after_step_id is not None and
                action.parameters['step_id'] == correction.after_step_id)
        if question or step:
            state.applied_corrections.add(index)
            state.record_fact(correction.field, correction.value, FactSource.USER_REPORTED, True)
            state.access_state[correction.field] = correction.value
            state.answer_overrides[correction.field] = correction.value
            state.log('user_correction', {'field': correction.field.value,
                                          'message': correction.message})
