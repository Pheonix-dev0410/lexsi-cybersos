from datetime import date

from cybersos.playbooks.loader import load_playbooks
from cybersos.playbooks.rules import PlaybookRegistry
from cybersos.project_paths import PLAYBOOKS_PATH, SOURCES_PATH


RULES_REVIEWED_ON = date(2026, 11, 15)


def load_project_registry(as_of: date = RULES_REVIEWED_ON) -> PlaybookRegistry:
    """The reviewed rule set shipped in `data/`, validated against its review date."""
    return load_playbooks(SOURCES_PATH, PLAYBOOKS_PATH, as_of=as_of)
