from collections.abc import Mapping
from dataclasses import dataclass

from cybersos.domain import TerminalState, ToolName
from cybersos.playbooks import PlaybookRegistry
from cybersos.simulator.observations import Observation
from cybersos.simulator.step_evidence import step_evidence, user_reported_evidence


@dataclass(frozen=True)
class ObservedProgress:
    """Step attempts, completions and terminal evidence a policy can derive from its own history."""

    attempted: frozenset[str]
    completed: frozenset[str]
    evidence: Mapping[TerminalState, frozenset[str]]
    asked: frozenset[str]


def observed_progress(observation: Observation, registry: PlaybookRegistry) -> ObservedProgress:
    attempted: set[str] = set()
    completed: set[str] = set()
    evidence: dict[TerminalState, set[str]] = {}
    asked: set[str] = set()
    for result in observation.history:
        if not result.ok:
            continue
        if result.tool_name == ToolName.ASK_ACCESS and 'field' in result.data:
            asked.add(str(result.data['field']))
        if result.tool_name != ToolName.SIMULATE_STEP or 'step_id' not in result.data:
            continue
        step = str(result.data['step_id'])
        attempted.add(step)
        rule = registry.rules[step]
        if 'provider_response' in result.data:
            step_completed, terminals = step_evidence(rule, str(result.data['provider_response']))
            if step_completed:
                completed.add(step)
        elif 'reported_response' in result.data:
            terminals = user_reported_evidence(rule, str(result.data['reported_response']))
        else:
            continue
        for terminal in terminals:
            evidence.setdefault(terminal, set()).add(step)
    return ObservedProgress(frozenset(attempted), frozenset(completed),
                            {terminal: frozenset(steps) for terminal, steps in evidence.items()},
                            frozenset(asked))
