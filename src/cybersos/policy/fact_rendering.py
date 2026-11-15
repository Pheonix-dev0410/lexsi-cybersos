from cybersos.domain import AccessField, Fact, FactSource
from cybersos.domain.access import normalize_value


def _checked(fact: Fact) -> Fact:
    if type(fact) is not Fact:
        raise TypeError('Expected core Fact')
    if (type(fact.revision) is not int or type(fact.correction) is not bool or
            type(fact.conflicted) is not bool):
        raise ValueError('Invalid fact provenance scalars')
    return fact


def _value(fact: Fact, value: object) -> str:
    field = AccessField(fact.field)
    return normalize_value(field, value).value


def render_fact_lines(facts: tuple[Fact, ...], history: tuple[Fact, ...]) -> list[str]:
    """One line per observed field: current value, its source, and every superseded report.

    Nothing is dropped to save tokens; earlier reports stay visible so corrections and
    conflicts can be reasoned about.
    """
    lines = []
    for fact in map(_checked, facts):
        notes = [FactSource(fact.source).value]
        if fact.correction:
            notes.append('correction')
        if fact.conflicted:
            notes.append('conflicting reports')
        if fact.reported_value is not None and _value(fact, fact.reported_value) != _value(fact, fact.value):
            notes.append(f'reported {_value(fact, fact.reported_value)}')
        for earlier in map(_checked, history):
            if earlier.field == fact.field and earlier.revision < fact.revision:
                reported = earlier.reported_value if earlier.reported_value is not None else earlier.value
                notes.append(f'earlier {_value(earlier, reported)} from {FactSource(earlier.source).value}')
        lines.append(f'{AccessField(fact.field).value} = {_value(fact, fact.value)} [{"; ".join(notes)}]')
    return lines
