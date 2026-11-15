from cybersos.data.independent_roots import independent_roots
from cybersos.data.root_generation import generate_roots
from cybersos.data.scenario_records import Split
from cybersos.data.scenario_wording import render_episodes
from cybersos.domain import AccessField, Availability, ObservedFacts, ProviderResponse
from cybersos.playbooks import PlaybookRegistry, Readiness, SimulationEffect, evaluate_prerequisites
from cybersos.simulator import EpisodeTools, RecoveryEnvironment


ALL_ROOTS = generate_roots() + independent_roots()


def test_paraphrases_are_seeded_and_share_their_root() -> None:
    root = generate_roots()[0]
    first = render_episodes(root, Split.TRAIN, seed=7, count=3)
    assert first == render_episodes(root, Split.TRAIN, seed=7, count=3)
    assert first != render_episodes(root, Split.TRAIN, seed=8, count=3)
    assert {episode.root.root_hash for episode in first} == {root.root_hash}
    assert len({episode.scenario.opening_message for episode in first}) == 3
    assert len({episode.scenario.scenario_id for episode in first}) == 3
    assert any('acount' in episode.scenario.opening_message for episode in first)


def test_every_requested_family_has_a_state_template() -> None:
    tags = {tag for root in generate_roots() for tag in root.tags}
    assert {'backup_codes', 'independent_factor', 'same_device_factor', 'trusted_session',
            'android_prerequisites', 'exposed_password', 'pending_recovery', 'uncertain_answers',
            'changed_answers', 'unauthorized_request', 'injected_sources',
            'temporary_tool_failures', 'unsupported_scope'} <= tags
    assert any(value == Availability.UNKNOWN for root in generate_roots()
               for value in root.scenario.access.values())


def test_hidden_ownership_agrees_with_intake_and_scenario_owner() -> None:
    for root in ALL_ROOTS:
        scenario = root.scenario
        owner = Availability.from_value(scenario.account_owner)
        assert scenario.access[AccessField.ACCOUNT_OWNER] == owner
        assert scenario.initial_facts[AccessField.ACCOUNT_OWNER] == owner
    assert {root.scenario.account_owner for root in generate_roots()} == {True, False}


def test_initial_facts_are_a_few_stated_facts_without_the_deciding_one() -> None:
    for root in ALL_ROOTS:
        scenario = root.scenario
        corrected = {correction.field for correction in scenario.corrections}
        assert 1 <= len(scenario.initial_facts) <= 4
        assert root.changed_field not in scenario.initial_facts
        for field, value in scenario.initial_facts.items():
            assert field in corrected or scenario.access[field] == value


def test_opening_message_states_volunteered_details_only() -> None:
    root = next(root for root in generate_roots()
                if AccessField.FIND_HUB_ENABLED in root.scenario.initial_facts and
                AccessField.VISIBLE_ON_GOOGLE_PLAY not in root.scenario.initial_facts)
    message = render_episodes(root, Split.TRAIN, seed=1)[0].scenario.opening_message
    stated = root.scenario.initial_facts[AccessField.FIND_HUB_ENABLED] == Availability.TRUE
    assert ('I had enabled Find Hub.' in message) == stated
    assert ('I had not enabled Find Hub.' in message) != stated
    assert 'Play device list' not in message


def test_restoration_eligibility_requires_a_successful_feasible_route(
        registry: PlaybookRegistry) -> None:
    for root in ALL_ROOTS:
        if not root.pair_id:
            continue
        scenario = root.scenario
        facts = ObservedFacts.from_mapping(scenario.access)
        feasible_success = []
        for rule in registry.lookup(scenario.provider, scenario.incident):
            if rule.simulation_effect != SimulationEffect.ATTEMPT_PROVIDER_VERIFICATION:
                continue
            response = scenario.provider_script.get(rule.id, scenario.provider_script.get(
                rule.simulation_effect.value, (ProviderResponse.CHALLENGE,)))[0]
            feasible_success.append(evaluate_prerequisites(rule, facts).status == Readiness.READY
                                    and response == ProviderResponse.SUCCESS)
        assert any(feasible_success) == root.restoration_eligible


def test_robustness_templates_schedule_real_simulator_events(registry: PlaybookRegistry) -> None:
    roots = generate_roots()
    corrected = next(root.scenario for root in roots if root.template_id == 'corrected_answer')
    failure = next(root.scenario for root in roots if root.template_id == 'temporary_failure')
    corrected_env = RecoveryEnvironment(corrected, registry, episode_id='generated-correction')
    EpisodeTools(corrected_env).ask_access('password_known')
    history = [fact for fact in corrected_env.observation().fact_history
               if fact.field == 'backup_code_accessible_now']
    assert [fact.value for fact in history] == ['true', 'false']
    assert history[-1].correction
    failure_env = RecoveryEnvironment(failure, registry, episode_id='generated-failure')
    tools = EpisodeTools(failure_env)
    for field in ('organization_managed', 'child_account', 'safe_other_device',
                  'independent_passkey_available'):
        tools.ask_access(field)
    assert tools.simulate_step('use_independent_passkey').error == 'temporary_tool_failure'
    assert not failure_env.trusted_snapshot().attempted_steps
    assert tools.simulate_step('use_independent_passkey').data['provider_response'] == 'success'
