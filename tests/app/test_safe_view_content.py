import pytest

from cybersos.app.access_questions import QUESTIONS, answer_choices
from cybersos.app.app_assets import AppAssets
from cybersos.app.incident_content import incident_content, official_links
from cybersos.app.incident_session import start_incident
from cybersos.domain import AccessField, Action, ToolName


def test_every_question_accepts_only_availability_or_storage_categories() -> None:
    assert set(QUESTIONS) == set(AccessField)
    for field in AccessField:
        choices = {value for _, value in answer_choices(field)}
        assert choices <= {'true', 'false', 'unknown', 'independent', 'same_locked_account'}
    assert 'never enter it' in QUESTIONS[AccessField.PASSWORD_KNOWN]
    assert 'Do not share' in QUESTIONS[AccessField.BACKUP_CODE_EXISTS]
    assert 'Do not share' in QUESTIONS[AccessField.REAUTHENTICATION_AVAILABLE]


def test_all_actionable_links_are_resolved_from_the_registry(app_assets: AppAssets) -> None:
    for rule in app_assets.registry.rules.values():
        assert {link.url for link in official_links(app_assets.registry, rule.source_ids)} <= {
            source.url for source in app_assets.registry.sources.values()}


def test_noncategory_input_is_rejected_before_it_can_enter_the_session(app_assets: AppAssets) -> None:
    session = start_incident(app_assets, 'account')
    private_value = 'a-value-that-is-not-an-availability-category'
    with pytest.raises(ValueError):
        session.answer(private_value)
    assert private_value not in str(session.runner.trace())
    assert not session.environment.observation().facts


def test_untrusted_model_proposal_is_never_rendered_as_instructions(app_assets: AppAssets) -> None:
    session = start_incident(app_assets, 'account')
    session.environment.report_access('true')
    raw = Action(ToolName.SIMULATE_STEP, {'step_id': 'official_account_recovery',
                 'url': 'https://attacker.invalid/<script>bad()</script>'}).to_json()
    trace = session.runner.run(lambda observation: raw)
    assert trace.unsafe_proposal_count > 0
    assert raw in [decision.raw_proposal for decision in trace.decisions]
    content = incident_content(session)
    assert 'attacker.invalid' not in str(content)
    assert '<script>' not in str(content)
