from cybersos.app.app_assets import AppAssets
from cybersos.app.practice_content import practice_content


def test_single_phone_removal_exposes_both_dependent_routes(app_assets: AppAssets) -> None:
    content = practice_content(app_assets)
    assert any('Signed-in main phone' in route for route in content.before_routes)
    assert any('Enrolled alternate number' in route for route in content.before_routes)
    assert not any('simulated access restored' in route for route in content.after_routes)
    assert any('official recovery pending' in route for route in content.after_routes)
    assert 'both depend on this phone' in content.gap
    assert 'Signed-in main phone: unavailable phone available' in content.gap
    assert 'Enrolled alternate number: unavailable alternate number accessible' in content.gap
    assert 'No direct recovery route remains' in content.gap
    assert 'independent method' in content.preparation
    assert {link.url for link in content.sources} == {app_assets.registry.sources['google_2sv'].url}


def test_an_independent_factor_preserves_a_recovery_route(app_assets: AppAssets) -> None:
    content = practice_content(app_assets, 'independent', 'phone')
    assert any('Independent passkey' in route and 'simulated access restored' in route
               for route in content.after_routes)
    assert 'No direct recovery route remains' not in content.gap


def test_drill_removes_only_the_chosen_factor(app_assets: AppAssets) -> None:
    content = practice_content(app_assets, 'independent', 'passkey')
    assert 'Independent passkey' in content.gap
    assert any('Signed-in main phone' in route for route in content.after_routes)
    assert app_assets.demos['preparedness'].access['phone_available'] == 'true'
