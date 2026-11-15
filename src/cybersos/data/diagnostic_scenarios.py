from dataclasses import dataclass
from pathlib import Path

from cybersos.data.decision_rows import Record
from cybersos.data.scenario_fingerprints import root_hash
from cybersos.data.scenario_loading import root_from_mapping
from cybersos.data.scenario_records import Bucket, ScenarioEpisode, ScenarioRoot, Split
from cybersos.domain import Scenario
from cybersos.serialization import read_jsonl


@dataclass(frozen=True)
class DiagnosticCase:
    scenario: Scenario
    root: ScenarioRoot
    family: str = ''
    split: str = 'diagnostic'
    expected_permissible_actions: tuple[str, ...] = ()
    terminal_boundary: str = ''
    paraphrase_id: str = ''

    @property
    def scenario_root_id(self) -> str:
        return self.root.root_id

    @property
    def episode(self) -> ScenarioEpisode:
        return ScenarioEpisode(self.scenario, self.root, Split.DEV,
                               self.paraphrase_id or self.scenario.scenario_id)


def _case(row: Record) -> DiagnosticCase:
    """Authored rows may omit generated root fields; saved split rows keep their own."""
    scenario = Scenario.from_mapping(row['scenario'])
    template = row.get('template_id', 'diagnostic')
    digest = row.get('root_hash') or root_hash(scenario, template)
    authored = {'template_id': template, 'root_hash': digest, 'bucket': Bucket.ROBUSTNESS,
                'tags': (), 'root_id': row.get('scenario_root_id', f'root-{digest}')}
    root = root_from_mapping(scenario, authored | row, tags=('diagnostic',))
    return DiagnosticCase(scenario, root, row.get('family', ''), row.get('split', 'diagnostic'),
                          tuple(row.get('expected_permissible_actions', ())),
                          row.get('terminal_boundary', ''), row.get('paraphrase_id', ''))


def load_diagnostic_scenarios(path: str | Path) -> tuple[DiagnosticCase, ...]:
    """Load authored or saved split rows; diagnostics are reserved for development."""
    cases: list[DiagnosticCase] = []
    for number, row in enumerate(read_jsonl(path), 1):
        try:
            cases.append(_case(row))
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            raise ValueError(f'{path}:{number}: invalid diagnostic scenario: {error}') from error
    if not cases:
        raise ValueError('Diagnostic input must contain at least one scenario')
    _validate_authored_cases(cases)
    return tuple(cases)


def _validate_authored_cases(cases: list[DiagnosticCase]) -> None:
    if len({case.scenario.scenario_id for case in cases}) != len(cases):
        raise ValueError('Diagnostic scenario IDs must be distinct')
    if not any(case.family for case in cases):
        return
    if len(cases) != 36 or len({case.family for case in cases}) != 6:
        raise ValueError('Authored diagnostics need 36 cases across six families')
    for family in {case.family for case in cases}:
        if any(sum(case.family == family and case.split == split for case in cases) != count
               for split, count in [('prompt_dev', 2), ('diagnostic', 4)]):
            raise ValueError('Each family needs two development and four diagnostic cases')
    roots = {split: {case.scenario_root_id for case in cases if case.split == split}
             for split in ('prompt_dev', 'diagnostic')}
    if roots['prompt_dev'] & roots['diagnostic']:
        raise ValueError('Prompt development and diagnostic roots overlap')
    if any(case.scenario.objective is None or not case.terminal_boundary for case in cases):
        raise ValueError('Every authored case needs a reviewed terminal boundary')
