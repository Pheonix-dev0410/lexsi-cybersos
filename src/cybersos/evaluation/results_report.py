import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Mapping

from cybersos.evaluation.cost_worksheet import serving_cost
from cybersos.evaluation.evaluation_config import EvaluationConfig
from cybersos.evaluation.metrics import summarize
from cybersos.evaluation.paired_bootstrap import BootstrapResult, compare_checkpoints
from cybersos.evaluation.recorded_runs import RecordedRun, check_weight_comparison, load_runs
from cybersos.evaluation.results_tables import PolicyResult, render_results_tables
from cybersos.serialization import to_json_value, write_json

MODEL_LABELS = ('B0', 'B1', 'B2', 'B3')


def report_results(directory: Path, output: Path, config: EvaluationConfig, *,
                   serving_costs: Mapping[str, float] | None = None) -> Path:
    """Report each comparable cohort separately; different case sets or contracts are never pooled."""
    sections, comparisons, summaries = ['CyberSOS measured evaluation results'], {}, {}
    for index, (key, cohort) in enumerate(_cohorts(load_runs(directory)).items(), 1):
        results = {label: PolicyResult(summarize(rows), observation_mode='structured',
                                       interface_disclosure='Q: guided availability controls' if label == 'Q'
                                       else 'R/model: observed structured facts')
                   for label, (_, rows) in cohort.items()}
        sections.extend([f'Cohort {index}: split={key[0]}; contract={key[1]}; scheduled={len(key[2])}',
                         render_results_tables(results), _cost_section(results, serving_costs or {})])
        summaries[str(index)] = {label: result.summary for label, result in results.items()}
        for name, difference in _paired_differences(index, cohort, config).items():
            comparisons[name] = difference
            sections.append(f'{name}: right-minus-left safe success, grouped by scenario root: '
                            f'{json.dumps(to_json_value(difference), sort_keys=True)}')
    sections.append('Missing experiments remain not run. Source applicability requires explicit adjudication; '
                    'absent labels remain unknown. No real recovery or usability claim.')
    output.mkdir(parents=True, exist_ok=True)
    destination = output / 'results.md'
    destination.write_text('\n\n'.join(sections) + '\n')
    write_json(output / 'results.json', {'summaries': summaries, 'paired_comparisons': comparisons})
    return destination


def _cohorts(runs: list[RecordedRun]) -> dict[tuple[object, ...], dict[str, RecordedRun]]:
    cohorts: dict[tuple[object, ...], dict[str, RecordedRun]] = defaultdict(dict)
    for path, rows in runs:
        identity = rows[0].identity
        key = (identity.split, identity.contract_hash, tuple(sorted(row.case.episode_id for row in rows)))
        if identity.model_id in cohorts[key]:
            raise ValueError(f'Multiple {identity.model_id} sweeps in one cohort; select the intended run directory')
        cohorts[key][identity.model_id] = path, rows
    return cohorts


def _paired_differences(index: int, cohort: dict[str, RecordedRun],
                        config: EvaluationConfig) -> dict[str, BootstrapResult]:
    differences = {}
    for left, right in combinations([label for label in MODEL_LABELS if label in cohort], 2):
        (left_path, left_rows), (right_path, right_rows) = cohort[left], cohort[right]
        check_weight_comparison(left_path, right_path)
        differences[f'cohort-{index}:{left}->{right}'] = compare_checkpoints(
            left_rows, right_rows, seed=config.seed, repetitions=config.bootstrap_repetitions)
    return differences


def _cost_section(results: Mapping[str, PolicyResult], serving_costs: Mapping[str, float]) -> str:
    lines = ['D. Serving cost on this workload, failures and retries included. '
             'Costs are actual bills supplied per policy; unsupplied costs stay undefined.']
    lines.extend(serving_cost(label, result.summary, serving_costs.get(label)).render()
                 for label, result in results.items() if result.summary is not None)
    return '\n'.join(lines)
