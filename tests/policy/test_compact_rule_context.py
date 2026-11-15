from cybersos.domain import Incident, Provider
from cybersos.playbooks import PlaybookRegistry
from cybersos.policy.retrieved_rule_rendering import render_rule_lines


def _parsed(lines: list[str]) -> dict[str, set[str]]:
    shared: set[str] = set()
    steps: dict[str, set[str]] = {}
    for line in lines:
        if line.startswith('Every retrieved step requires '):
            shared = set(line.removeprefix('Every retrieved step requires ').rstrip('.').split(', '))
            continue
        names, rest = line.split(': ', 1)
        condition = rest.rsplit(' [', 1)[0]
        required = set() if condition == 'nothing further' else set(condition.split(', '))
        for name in names.split(', '):
            steps[name] = required
    return {name: required | shared for name, required in steps.items()}


def test_grouped_rule_context_keeps_every_step_and_prerequisite(registry: PlaybookRegistry) -> None:
    for provider in Provider:
        for incident in Incident:
            rules = [{'step_id': rule.id, 'source_ids': list(rule.source_ids),
                      'requires': {field.value: value.value for field, value in rule.requires.items()}}
                     for rule in registry.lookup(provider, incident)]
            if not rules:
                continue
            expected = {rule['step_id']: {f'{field}={value}' for field, value in rule['requires'].items()}
                        for rule in rules}
            assert _parsed(render_rule_lines(rules)) == expected
