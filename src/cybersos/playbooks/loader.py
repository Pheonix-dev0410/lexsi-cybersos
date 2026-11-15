import re
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from cybersos.domain import AccessField, Availability, FactValue, Incident, Provider
from cybersos.domain.access import normalize_value
from cybersos.domain.sensitive_text import contains_url
from cybersos.playbooks.rules import (
    PlaybookRegistry, RecoveryRule, RiskLevel, SimulationEffect, Source,
)
from cybersos.playbooks.source_registry import OFFICIAL_DESTINATIONS
from cybersos.serialization import load_strict_yaml


class PlaybookValidationError(ValueError):
    pass


_SOURCE_FIELDS = {'id', 'url', 'title', 'scope', 'checked_on'}
_RULE_FIELDS = {'id', 'provider', 'incident', 'source_ids', 'checked_on', 'requires', 'scope_note',
                'unknown_requires_question', 'user_instruction', 'simulation_effect',
                'real_account_effect', 'risk_level'}
_REVIEW_STATUSES = {'source_checked', 'needs_human_review'}


def load_playbooks(sources_path: str | Path, playbooks_path: str | Path,
                   *, as_of: date) -> PlaybookRegistry:
    """Load and validate authored YAML; the caller supplies the review clock."""
    try:
        sources: dict[str, Source] = {}
        for data in _read(sources_path):
            source = _parse_source(data, as_of)
            if source.id in sources:
                raise PlaybookValidationError('Duplicate source or unapproved destination')
            sources[source.id] = source
        rules: dict[str, RecoveryRule] = {}
        for data in _read(playbooks_path):
            rule = _parse_rule(data, sources, as_of)
            if rule.id in rules:
                raise PlaybookValidationError('Duplicate rule')
            rules[rule.id] = rule
        if not sources or not rules:
            raise PlaybookValidationError('Empty registry')
        return PlaybookRegistry(sources, rules)
    except (KeyError, TypeError, ValueError, yaml.YAMLError) as error:
        raise PlaybookValidationError(str(error)) from error


def _read(path: str | Path) -> list[dict[str, Any]]:
    values = load_strict_yaml(path)
    if not isinstance(values, list) or not all(isinstance(item, dict) for item in values):
        raise PlaybookValidationError('Registry must be a list of mappings')
    return values


def _parse_source(data: dict[str, Any], as_of: date) -> Source:
    _require_shape(data, _SOURCE_FIELDS)
    if not isinstance(data['title'], str) or not isinstance(data['scope'], list):
        raise PlaybookValidationError('Source title/scope has an invalid type')
    source_id = _identifier(data['id'])
    if data['url'] != OFFICIAL_DESTINATIONS[source_id]:
        raise PlaybookValidationError('Duplicate source or unapproved destination')
    source = Source(source_id, data['url'], data['title'],
                    tuple(Provider(provider) for provider in data['scope']),
                    _checked(data['checked_on'], as_of))
    if not source.scope or not source.title.strip():
        raise PlaybookValidationError('Empty source scope or title')
    return source


def _parse_rule(data: dict[str, Any], sources: Mapping[str, Source], as_of: date) -> RecoveryRule:
    _require_shape(data, _RULE_FIELDS, frozenset({'review_status'}))
    if (not isinstance(data['requires'], dict) or not data['requires'] or
            not isinstance(data['source_ids'], list) or
            not isinstance(data['incident'], (str, list))):
        raise PlaybookValidationError('Invalid predicate, source, or incident collection')
    review_status = data.get('review_status', 'source_checked')
    if review_status not in _REVIEW_STATUSES:
        raise PlaybookValidationError('Invalid review status')
    rule_id = _identifier(data['id'])
    provider = Provider(data['provider'])
    source_ids = tuple(data['source_ids'])
    if len(source_ids) != len(set(source_ids)):
        raise PlaybookValidationError('Duplicate source references')
    if not source_ids or any(provider not in sources[source].scope for source in source_ids):
        raise PlaybookValidationError('Rule outside source scope')
    incidents = data['incident'] if isinstance(data['incident'], list) else [data['incident']]
    incidents = tuple(Incident(incident) for incident in incidents)
    if not incidents or data['unknown_requires_question'] is not True:
        raise PlaybookValidationError('Rules must clarify unknown prerequisites')
    if data['real_account_effect'] != 'none':
        raise PlaybookValidationError('Real account effects are forbidden')
    for key in ('scope_note', 'user_instruction'):
        if not isinstance(data[key], str) or not data[key].strip():
            raise PlaybookValidationError('Missing authored scope/instruction')
        if contains_url(data[key]):
            raise PlaybookValidationError('Destinations belong in the source registry')
    requires = _requirements(data['requires'])
    effect = SimulationEffect(data['simulation_effect'])
    if effect != SimulationEffect.PROVIDER_ADMIN_HANDOFF and any(
            requires.get(field) != Availability.FALSE
            for field in (AccessField.ORGANIZATION_MANAGED, AccessField.CHILD_ACCOUNT)):
        raise PlaybookValidationError('Personal-account rules must exclude managed/child scope')
    risk = RiskLevel(data['risk_level'])
    if effect == SimulationEffect.ERASE_DEVICE and risk != RiskLevel.HIGH:
        raise PlaybookValidationError('Erasure must be high risk')
    checked = _checked(data['checked_on'], as_of)
    if any(checked > sources[source].checked_on for source in source_ids):
        raise PlaybookValidationError('Rule review exceeds source review')
    return RecoveryRule(rule_id, provider, incidents, source_ids, checked, requires,
                        data['scope_note'], True, data['user_instruction'], effect,
                        'none', risk, review_status)


def _requirements(values: dict[str, Any]) -> dict[AccessField, FactValue]:
    requires = {AccessField(key): normalize_value(AccessField(key), value) for key, value in values.items()}
    if any(value == Availability.UNKNOWN for value in requires.values()):
        raise PlaybookValidationError('Prerequisite expectations must be definite')
    if requires.get(AccessField.ACCOUNT_OWNER) != Availability.TRUE:
        raise PlaybookValidationError('Rules require attested ownership')
    return requires


def _checked(value: object, as_of: date) -> date:
    checked = date.fromisoformat(str(value))
    if checked > as_of:
        raise PlaybookValidationError('Review date is in the future')
    return checked


def _identifier(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r'[a-z][a-z0-9_]*', value):
        raise PlaybookValidationError('Invalid identifier')
    return value


def _require_shape(data: dict[str, Any], required: set[str],
                   optional: frozenset[str] = frozenset()) -> None:
    if not required <= data.keys() or not data.keys() <= required | optional:
        raise PlaybookValidationError('Missing or extra registry fields')
