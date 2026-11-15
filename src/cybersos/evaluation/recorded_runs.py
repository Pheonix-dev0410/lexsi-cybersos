from pathlib import Path

from cybersos.evaluation.trace_records import TraceRecord
from cybersos.evaluation.trace_serialization import load_traces
from cybersos.serialization import read_json

RecordedRun = tuple[Path, tuple[TraceRecord, ...]]

_MATCHED_SETTINGS = ('model_revision', 'precision', 'context_budget', 'action_budget', 'evaluation_seeds',
                     'decoding', 'observation_mode', 'scorer_version', 'lexsi_commits')
_MATCHED_HASHES = ('data', 'split', 'source_corpus', 'prompt', 'simulator', 'tools', 'guard', 'runtime',
                   'orchestration', 'eval_config')


def load_runs(directory: Path) -> list[RecordedRun]:
    paths = sorted(directory.rglob('traces.jsonl'))
    if not paths:
        raise ValueError(f'No traces.jsonl runs found under {directory}')
    runs = [(path, load_traces(path)) for path in paths]
    if any(not rows or len({row.identity for row in rows}) != 1 for _, rows in runs):
        raise ValueError('Each trace file must contain one nonempty run')
    ids = [rows[0].identity.run_id for _, rows in runs]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate run identities; select a single copy of each sweep')
    return runs


def check_weight_comparison(left: Path, right: Path) -> None:
    """Two checkpoints may be compared only when everything but the weights was held fixed."""
    manifests = [read_json(path.with_name('manifest.json')) for path in (left, right)]
    for key in _MATCHED_SETTINGS:
        if manifests[0][key] != manifests[1][key]:
            raise ValueError(f'Weight comparisons require matching manifest field: {key}')
    for key in _MATCHED_HASHES:
        if manifests[0]['hashes'][key] != manifests[1]['hashes'][key]:
            raise ValueError(f'Weight comparisons require matching {key} hashes')
    locks = [sorted(manifest['environment_lockfiles'].values()) for manifest in manifests]
    if locks[0] != locks[1]:
        raise ValueError('Weight comparisons require one shared evaluation environment')
