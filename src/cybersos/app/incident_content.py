from dataclasses import dataclass

from cybersos.app.access_questions import QUESTIONS, access_label, answer_choices, availability_label
from cybersos.app.incident_session import IncidentSession
from cybersos.domain import AccessField, ExecutionStatus, TerminalState, ToolName
from cybersos.playbooks import PlaybookRegistry, RecoveryRule
from cybersos.simulator import RecoveryEnvironment


USER_REPORTED_COMPLETION = 'User-reported completion. Access and account changes are not independently verified.'
TERMINAL_LABELS = {
    TerminalState.PROTECTIVE_WORKFLOW_COMPLETED: USER_REPORTED_COMPLETION,
    TerminalState.OFFICIAL_RECOVERY_PENDING: 'Official recovery pending. Await the provider decision.',
    TerminalState.NEEDS_PROVIDER_OR_ADMIN: 'Provider or administrator handoff required.',
    TerminalState.NO_SUPPORTED_PATH_KNOWN: 'No supported route is known from the access reported.',
    TerminalState.UNSAFE_REQUEST_DECLINED: 'Only the account owner’s authorized recovery is supported.',
    TerminalState.BUDGET_EXHAUSTED: 'This guidance session reached its step limit. Use official support.',
    TerminalState.INVALID_FINISH: 'The proposed conclusion could not be supported.',
    TerminalState.ENVIRONMENT_ERROR: 'Guidance is unavailable. Consult the official provider instructions.',
}
STOPPED_LABELS = {
    ExecutionStatus.TIMEOUT: 'The serving model timed out, so this guidance session ended. '
                             'Use the official provider instructions.',
    ExecutionStatus.GENERATION_ERROR: 'The serving model failed to respond, so this guidance session ended. '
                                      'Use the official provider instructions.',
}
GUIDANCE_ONLY = 'Guidance only. No live account connection; access is not independently verified.'


@dataclass(frozen=True)
class OfficialLink:
    title: str
    url: str


@dataclass(frozen=True)
class IncidentContent:
    status: str
    policy: str
    known_access: list[list[str]]
    question: str = ''
    choices: tuple[tuple[str, str], ...] = ()
    instruction: str = ''
    needs: str = ''
    failure: str = ''
    sources: tuple[OfficialLink, ...] = ()


def official_links(registry: PlaybookRegistry, source_ids: tuple[str, ...]) -> tuple[OfficialLink, ...]:
    return tuple(OfficialLink(registry.sources[key].title, url)
                 for key, url in zip(source_ids, registry.destinations(source_ids), strict=True))


def step_requirements(rule: RecoveryRule) -> str:
    return '\n'.join(f'{access_label(field)}: {availability_label(value.value)}'
                     for field, value in rule.requires.items())


def incident_content(session: IncidentSession) -> IncidentContent:
    env = session.environment
    observation = env.observation()
    basis = 'Synthetic demo inputs · ' if session.synthetic else ''
    status = basis + _status(env)
    reports = [result for result in observation.history if 'reported_response' in result.data]
    if reports:
        status += f' Last result (user-reported): {reports[-1].data["reported_response"]}.'
    rows = [[access_label(fact.field), availability_label(fact.value.value),
             'synthetic intake' if session.synthetic and fact.source.value == 'intake'
             else fact.source.value.replace('_', ' ')] for fact in observation.facts]
    base = dict(status=status, policy=session.policy_label, known_access=rows)
    if env.done or not env.awaiting_report:
        return IncidentContent(**base)
    result = observation.history[-1]
    if result.tool_name == ToolName.ASK_ACCESS:
        field = AccessField(result.data['field'])
        return IncidentContent(**base, question=QUESTIONS[field], choices=tuple(answer_choices(field)))
    rule = env.registry.rules[str(result.data['step_id'])]
    return IncidentContent(
        **base, instruction=rule.user_instruction, needs=step_requirements(rule),
        failure='Report only: completed, more verification requested, pending review, or unable to complete. '
                'Do not send any credentials or verification values.',
        sources=official_links(env.registry, rule.source_ids))


def _status(env: RecoveryEnvironment) -> str:
    """An incident episode that finishes without a terminal ended on the user's own completion report."""
    if env.done and env.terminal_state is None:
        if env.execution_status == ExecutionStatus.FINISHED:
            return USER_REPORTED_COMPLETION
        return STOPPED_LABELS.get(env.execution_status,
                                  'Guidance stopped before completion. Use the official provider instructions.')
    return TERMINAL_LABELS.get(env.terminal_state, GUIDANCE_ONLY)
