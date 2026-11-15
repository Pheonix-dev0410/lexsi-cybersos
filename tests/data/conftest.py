import json
from pathlib import Path

import pytest

from cybersos.data.scenario_records import ScenarioEpisode
from cybersos.data.root_generation import generate_roots
from cybersos.data.scenario_fingerprints import scenario_mapping
from cybersos.data.split_assignment import build_scenario_splits


@pytest.fixture(scope='module')
def diagnostic_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp('diagnostics') / 'small_diagnostic_fixture.jsonl'
    roots = [root for root in generate_roots() if root.pair_id is None][:36]
    rows = [{'scenario': scenario_mapping(root.scenario), 'root_id': root.root_id,
             'template_id': root.template_id, 'bucket': root.bucket.value,
             'tags': ['diagnostic_fixture']} for root in roots]
    path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
    return path


@pytest.fixture(scope='module')
def full_splits(diagnostic_path: Path) -> tuple[ScenarioEpisode, ...]:
    return build_scenario_splits(diagnostic_path, seed=20261113)


@pytest.fixture(scope='module')
def reduced_splits(diagnostic_path: Path) -> tuple[ScenarioEpisode, ...]:
    return build_scenario_splits(diagnostic_path, seed=20261113, profile='reduced')
