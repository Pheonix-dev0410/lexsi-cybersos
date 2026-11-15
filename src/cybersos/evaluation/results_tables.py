from dataclasses import dataclass
from typing import Mapping

from cybersos.evaluation.metric_types import MetricSummary, Rate
from cybersos.serialization import to_json_value


@dataclass(frozen=True)
class PolicyResult:
    summary: MetricSummary | None
    gate_reason: str | None = None
    observation_mode: str = 'not declared'
    free_text_coverage: str = 'not measured'
    interface_disclosure: str = 'not declared'


def _table(headers: tuple[str, ...], rows: list[list[str]]) -> str:
    def line(cells: list[str] | tuple[str, ...]) -> str:
        return '| ' + ' | '.join(str(cell).replace('|', '\\|').replace('\n', ' ') for cell in cells) + ' |'
    return '\n'.join([line(headers), line(['---'] * len(headers)), *(line(row) for row in rows)])


def _missing(result: PolicyResult | None) -> str:
    return 'not run' + (f' ({result.gate_reason})' if result and result.gate_reason else '')


def _has_run(result: PolicyResult | None) -> bool:
    return bool(result and result.summary and
                result.summary.scheduled > result.summary.execution_statuses['not_run'])


def _rate(summary: MetricSummary, name: str) -> str:
    return summary.rates[name].render(critical=name == 'critical_unsafe_episodes')


def _number(value: float | None) -> str:
    return 'not measured' if value is None else f'{value:.2f}'


def render_results_tables(results: Mapping[str, PolicyResult], *, selected_model: str = 'B1') -> str:
    a_rows, b_rows, c_rows = [], [], []
    for policy, label in (('Q', 'Q: guided questionnaire'),
                          (selected_model, f'{selected_model}: selected model-assisted workflow')):
        result = results.get(policy)
        if not _has_run(result):
            a_rows.append([label] + [_missing(result)] * 5)
            continue
        summary = result.summary
        questions, turns = summary.efficiency['all_questions'], summary.efficiency['all_turns']
        burden = (f'{questions.total:g} questions ({questions.measured}/{questions.denominator} measured); '
                  f'{turns.total:g} turns ({turns.measured}/{turns.denominator} measured)')
        a_rows.append([label, _rate(summary, 'safe_eligible_completion'),
                       _rate(summary, 'correct_boundary_handling'), burden,
                       _rate(summary, 'corrections_handled'),
                       f'{result.free_text_coverage} / {result.observation_mode}'])
    for policy, label in (('R', 'R: observed-state rules'), ('B0', 'B0: Tiny Aya base'),
                          ('B1', 'B1: SFT'), ('B2', 'B2: SFT + AgentTune')):
        result = results.get(policy)
        if not _has_run(result):
            b_rows.append([label] + [_missing(result)] * 5)
        else:
            b_rows.append([label] + [_rate(result.summary, name) for name in (
                'safe_eligible_completion', 'correct_boundary_handling', 'impossible_action_episodes',
                'critical_unsafe_episodes', 'benign_over_refusal')])
    for policy, result in results.items():
        if not _has_run(result):
            c_rows.append([policy] + [_missing(result)] * 5)
            continue
        summary = result.summary
        latency = summary.efficiency['all_latency_seconds']
        c_rows.append([policy, _rate(summary, 'output_format_errors'), _rate(summary, 'revision_handling'),
                       _number(summary.efficiency['successful_calls'].median),
                       f'{_number(latency.median)} / {_number(latency.p95)} seconds; '
                       f'{latency.measured}/{latency.denominator} measured',
                       'execution: ' + str({s: Rate(n, summary.scheduled).render()
                                            for s, n in summary.execution_statuses.items()}) +
                       '; outcomes: ' + str({s: Rate(n, summary.scheduled).render()
                                             for s, n in summary.task_outcomes.items()})])
    sections = [
        'A. Product comparison on matched scenarios. Scripted questions are burden proxies; '
        'real user effort is not measured.',
        _table(('Workflow', 'Safe eligible completion', 'Correct boundary handling',
                'Questions and total turns', 'User corrections handled', 'Free-text coverage / observation mode'), a_rows),
        'B. Policy comparison under the frozen model-facing harness.',
        _table(('Policy', 'Safe eligible completion', 'Correct boundary handling', 'Impossible-action episodes',
                'Critical unsafe episodes', 'Benign over-refusal'), b_rows),
        'C. Diagnostics and efficiency.',
        _table(('Policy', 'Output-format errors', 'Revision handling (corrections and tool failures)',
                'Median successful calls', 'All-case latency p50/p95', 'Execution statuses and task outcomes reported separately'), c_rows),
    ]
    for policy, result in results.items():
        if result.summary:
            summary = result.summary
            sections.extend([f'{policy} interface: {result.interface_disclosure}',
                             f'{policy} policy layer: {summary.policy_counts}',
                             f'{policy} system layer: {summary.system_counts}',
                             f'{policy} detailed terminals: {summary.terminals}',
                             f'{policy} overlapping diagnostic flags: {summary.diagnostic_flags}',
                             f'{policy} all metrics: {to_json_value(summary.rates)}'])
    return '\n\n'.join(sections) + '\n'
