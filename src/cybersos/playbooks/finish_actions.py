from cybersos.domain import Action, TerminalState, ToolName
from cybersos.playbooks.rules import PlaybookRegistry


def finish_action(status: TerminalState, registry: PlaybookRegistry,
                  step_id: str | None = None) -> Action:
    """A finish citing exactly the registry sources of its next step."""
    sources = registry.rules[step_id].source_ids if step_id else ()
    return Action(ToolName.FINISH, {'status': status.value, 'next_step_id': step_id,
                                   'source_ids': sources})
