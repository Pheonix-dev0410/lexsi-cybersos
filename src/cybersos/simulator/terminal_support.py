from collections.abc import Collection, Mapping

from cybersos.domain import Availability, FactSource, Incident, ObservedFacts, Provider, TerminalState
from cybersos.playbooks import PlaybookRegistry, Readiness, evaluate_prerequisites
from cybersos.safety import assistance_declined


def supported_conclusions(registry: PlaybookRegistry, facts: ObservedFacts,
                          provider: Provider, incident: Incident,
                          evidence: Mapping[TerminalState, Collection[str]], completed: Collection[str],
                          required: tuple[str, ...], *, opening_message: str,
                          attempted: frozenset[str] = frozenset()) -> frozenset[TerminalState]:
    supported = set(evidence)
    if required and set(required) <= set(completed):
        supported.add(TerminalState.PROTECTIVE_WORKFLOW_COMPLETED)
    if assistance_declined(facts, opening_message):
        supported.add(TerminalState.UNSAFE_REQUEST_DECLINED)
    applicable = registry.lookup(provider, incident)
    answered_unknown = {fact.field for fact in facts.snapshot()
                        if fact.value == Availability.UNKNOWN and not fact.conflicted and
                        fact.source in {FactSource.SCRIPTED_ANSWER, FactSource.USER_REPORTED}}
    results = [(rule, evaluate_prerequisites(rule, facts)) for rule in applicable]
    if not evidence and applicable and all(
            rule.id in attempted or result.status == Readiness.BLOCKED or
            (result.status == Readiness.NEEDS_INFORMATION and
             bool(answered_unknown.intersection(result.unknown_fields)))
            for rule, result in results):
        supported.add(TerminalState.NO_SUPPORTED_PATH_KNOWN)
    return frozenset(supported)
