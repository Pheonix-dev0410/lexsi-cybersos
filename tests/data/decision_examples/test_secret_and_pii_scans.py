import pytest

from cybersos.data.decision_examples import DecisionExamples
from cybersos.data.decision_rows import row_hash
from cybersos.data.decision_gates import DecisionGates
from cybersos.playbooks import PlaybookRegistry


@pytest.mark.parametrize('secret', [
    'My password is CorrectHorse9', 'verification code: 123456', 'backup code: 12345678',
    'session_token=abcdef123456', 'My email is example@example.com',
    'Call +1 (415) 555-1212', 'my name is Jane Doe',
    '-----BEGIN PRIVATE KEY-----', 'Bearer abcdefghijklmnop',
])
def test_sensitive_row_is_rejected(secret: str, examples: DecisionExamples,
                                    registry: PlaybookRegistry) -> None:
    row = dict(examples.rows[0])
    origins = examples.provenance[row_hash(row)]
    row['instruction'] = row['instruction'].replace('Observed facts', secret + '. Observed facts')
    errors = DecisionGates(list(examples.trajectories), registry).check(row, origins)
    assert any(reason.startswith('privacy:') for reason in errors)
