import pytest

from cybersos.playbooks import PlaybookRegistry, load_project_registry


@pytest.fixture(scope='session')
def registry() -> PlaybookRegistry:
    return load_project_registry()
