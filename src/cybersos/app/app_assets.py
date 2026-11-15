from dataclasses import dataclass
from pathlib import Path

from cybersos.app.demo_cases import demo_scenarios
from cybersos.domain import Scenario
from cybersos.playbooks import PlaybookRegistry, load_project_registry

ARTIFACT_DIRECTORY = Path(__file__).parent / 'saved_traces'


@dataclass(frozen=True)
class AppAssets:
    registry: PlaybookRegistry
    demos: dict[str, Scenario]


def load_app_assets() -> AppAssets:
    return AppAssets(load_project_registry(), demo_scenarios())
