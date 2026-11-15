from dataclasses import fields

from cybersos.data.decision_rows import Record
from cybersos.serialization import canonical_json_sha256
from cybersos.domain import Action, Incident, Provider, Scenario
from cybersos.serialization import to_json_value
from cybersos.playbooks import PlaybookRegistry


def source_evidence(scenario: Scenario, registry: PlaybookRegistry) -> Record:
    rules = registry.lookup(scenario.provider, scenario.incident)
    versions = {rule.id: canonical_json_sha256({item.name: (getattr(rule, item.name).isoformat()
                if item.name == 'checked_on' else to_json_value(getattr(rule, item.name)))
                for item in fields(rule)}) for rule in rules}
    source_ids = sorted({source for rule in rules for source in rule.source_ids})
    sources = {key: {'url': registry.sources[key].url, 'title': registry.sources[key].title,
                     'checked_on': registry.sources[key].checked_on.isoformat(),
                     'scope': [scope.value for scope in registry.sources[key].scope]}
               for key in source_ids}
    context = '\n'.join(f'{rule.id}: {rule.scope_note} {rule.user_instruction} '
                        f"Sources: {', '.join(rule.source_ids)}" for rule in rules)
    return {'rule_versions': versions, 'sources': sources, 'source_context': context,
            'provider': scenario.provider.value, 'incident': scenario.incident.value}


def evidence_errors(evidence: Record, action: Action, scenario: Scenario,
                    registry: PlaybookRegistry) -> list[str]:
    errors = []
    expected = source_evidence(scenario, registry)
    if not evidence.get('source_context'):
        errors.append('missing_source_evidence')
    if evidence != expected:
        errors.append('source_provenance_mismatch')
    for source_id in evidence.get('sources', {}):
        source = registry.sources.get(source_id)
        if source is None or Provider(scenario.provider) not in source.scope:
            errors.append('source_scope')
    step = action.parameters.get('step_id', action.parameters.get('next_step_id'))
    if step is not None:
        rule = registry.rules.get(step)
        if (rule is None or rule.provider != scenario.provider or
                Incident(scenario.incident) not in rule.incident):
            errors.append('rule_scope')
        elif not set(rule.source_ids) <= set(evidence.get('sources', {})):
            errors.append('missing_source_evidence')
    for source_id in action.parameters.get('source_ids', ()):
        if source_id not in registry.sources or scenario.provider not in registry.sources[source_id].scope:
            errors.append('source_scope')
    return errors
