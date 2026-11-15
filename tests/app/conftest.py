import pytest

from cybersos.app.app_assets import AppAssets, load_app_assets


@pytest.fixture(scope='session')
def app_assets() -> AppAssets:
    return load_app_assets()
