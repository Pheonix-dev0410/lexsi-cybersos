from pathlib import Path

import pytest
import yaml

from cybersos.domain import Availability, ObservedFacts
from cybersos.playbooks import (
    RULES_REVIEWED_ON, PlaybookRegistry, PlaybookValidationError, Readiness, evaluate_prerequisites,
    load_playbooks,
)
from cybersos.project_paths import PLAYBOOKS_PATH, SOURCES_PATH


def test_every_rule_has_positive_blocked_and_unknown_case(registry: PlaybookRegistry) -> None:
    assert 12 <= len(registry.rules) <= 20
    for rule in registry.rules.values():
        facts = {field: value for field, value in rule.requires.items()}
        assert evaluate_prerequisites(rule, ObservedFacts.from_mapping(facts)).status == Readiness.READY
        field = next(iter(facts))
        expected = facts[field]
        facts[field] = Availability.FALSE if expected == Availability.TRUE else Availability.TRUE
        assert evaluate_prerequisites(rule, ObservedFacts.from_mapping(facts)).status == Readiness.BLOCKED
        del facts[field]
        assert evaluate_prerequisites(rule, ObservedFacts.from_mapping(facts)).status == Readiness.NEEDS_INFORMATION


@pytest.mark.parametrize(('target', 'field', 'value'), [
    ('rule', 'requires', []), ('rule', 'requires', {}),
    ('rule', 'requires', {'account_owner': 'unknown'}),
    ('source', 'title', 1), ('source', 'scope', 'google_personal'),
    ('rule', 'source_ids', ['invented']), ('rule', 'provider', 'not_google'),
    ('rule', 'checked_on', '2026-11-16'), ('rule', 'checked_on', 'not_a_date'),
    ('rule', 'requires', {'secret_password': True}),
    ('rule', 'requires', {'phone_available': 'maybe'}),
    ('rule', 'real_account_effect', 'erase'), ('rule', 'scope_note', ''),
    ('rule', 'unknown_requires_question', False),
    ('rule', 'user_instruction', 'Visit https://evil.example/'),
    ('source', 'url', 'https://support.google.com.evil.example/'),
    ('source', 'scope', ['android']), ('source', 'checked_on', '2026-11-16'),
])
def test_invalid_authored_registry_rejected(tmp_path: Path, target: str, field: str, value: object) -> None:
    sources = yaml.safe_load(SOURCES_PATH.read_text())
    rules = yaml.safe_load(PLAYBOOKS_PATH.read_text())
    (rules if target == 'rule' else sources)[0][field] = value
    source_path, rule_path = tmp_path / 'sources.yaml', tmp_path / 'rules.yaml'
    source_path.write_text(yaml.safe_dump(sources))
    rule_path.write_text(yaml.safe_dump(rules))
    with pytest.raises(PlaybookValidationError):
        load_playbooks(source_path, rule_path, as_of=RULES_REVIEWED_ON)


def test_duplicate_yaml_predicates_rejected(tmp_path: Path) -> None:
    path = tmp_path / 'rules.yaml'
    path.write_text('- {id: one, id: two}\n')
    with pytest.raises(PlaybookValidationError, match='Duplicate YAML key'):
        load_playbooks(SOURCES_PATH, path, as_of=RULES_REVIEWED_ON)
