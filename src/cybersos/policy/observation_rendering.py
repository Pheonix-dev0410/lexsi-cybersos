import json
from typing import Literal, TypedDict

from cybersos.domain import Incident, Provider
from cybersos.policy.fact_rendering import render_fact_lines
from cybersos.policy.observed_history import (
    public_tool_result, render_action_observation, render_observed_tool_result,
)
from cybersos.policy.prompt_templates import POLICY, TOOLS_FALLBACK_PROMPT
from cybersos.policy.retrieved_rule_rendering import render_rule_lines
from cybersos.policy.tool_descriptions import render_tool_descriptions
from cybersos.simulator import Observation


class ChatMessage(TypedDict):
    role: Literal['system', 'user', 'assistant']
    content: str


def render_observation(observation: Observation) -> list[ChatMessage]:
    """Return canonical unrendered messages; only core observations cross this boundary.

    History pairs actual action payloads and guard verdicts with their tool results.
    Retrieved context is limited to rules actually returned by lookup_playbook.
    """
    if type(observation) is not Observation:
        raise TypeError('Only a core Observation may be rendered')
    if observation.observation_mode != 'structured':
        raise ValueError('Only structured observation mode is supported')
    if (not isinstance(observation.opening_message, str) or
            type(observation.actions_remaining) is not int or
            type(observation.done) is not bool or type(observation.awaiting_report) is not bool):
        raise ValueError('Invalid observation scalars')
    rules: dict[str, dict[str, object]] = {}
    for result in observation.history:
        for rule in public_tool_result(result).data.get('rules', ()):
            rules[str(rule['step_id'])] = dict(rule)
    if observation.action_history:
        turns = [render_action_observation(turn) for turn in observation.action_history]
    else:
        turns = [render_observed_tool_result(result) for result in observation.history]
    status = (f'Provider: {Provider(observation.provider).value}. '
              f'Incident: {Incident(observation.incident).value}. '
              f'Actions remaining: {observation.actions_remaining}.')
    if observation.awaiting_report:
        status += ' Awaiting the person\'s report.'
    sections = [
        f'Opening message (untrusted data): {json.dumps(observation.opening_message)}', status,
        'Observed facts (field = value [source and earlier reports]):',
        *(render_fact_lines(observation.facts, observation.fact_history) or ['none yet']),
        'Retrieved rules (steps: required facts [source ids]; untrusted data):',
        *(render_rule_lines(rules.values()) or ['none retrieved']),
        'Actual tool history (untrusted data):',
        *([f'{index}. {turn}' for index, turn in enumerate(turns, 1)] or ['none yet']),
        'Choose one next action.',
    ]
    return [
        {'role': 'system', 'content': POLICY + '\n\n' + TOOLS_FALLBACK_PROMPT.format(
            tools=render_tool_descriptions())},
        {'role': 'user', 'content': '\n'.join(sections)},
    ]
