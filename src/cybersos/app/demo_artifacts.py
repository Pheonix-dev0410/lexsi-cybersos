from pathlib import Path

from cybersos.app.app_assets import ARTIFACT_DIRECTORY, AppAssets
from cybersos.app.demo_cases import DEMO_TEMPLATE_ID
from cybersos.baselines import ObservedStatePlanner
from cybersos.data.scenario_fingerprints import root_hash
from cybersos.evaluation import RunIdentity, run_batch, schedule_scenario, write_traces
from cybersos.evaluation.run_versions import rule_baseline_checkpoint
from cybersos.policy import load_serving_contract


def prepare_demo_traces(assets: AppAssets, destination: Path = ARTIFACT_DIRECTORY / 'baseline.jsonl') -> Path:
    """Write only deliberately synthetic benchmark runs; never pass an incident session here."""
    identity = RunIdentity(f'{DEMO_TEMPLATE_ID}-r', 'R observed-state rule planner', rule_baseline_checkpoint(),
                           load_serving_contract().contract_hash, 'demo')
    records = []
    for key, scenario in assets.demos.items():
        case = schedule_scenario(scenario, root_hash(scenario, DEMO_TEMPLATE_ID), episode_id=f'demo-{key}')
        # One batch per demo: the planner is told that demo's published protective workflow.
        planner = ObservedStatePlanner(assets.registry, scenario.required_protective_steps)
        # A fixed clock keeps the bundled artifact byte-reproducible; demo replays are not timing evidence.
        records.extend(run_batch((case,), lambda: planner, assets.registry, identity, clock=lambda: 0.0))
    write_traces(destination, records)
    return destination
