import json
from typing import Any

from cybersos.policy import render_observation
from cybersos.serialization import canonical_json_sha256
from cybersos.simulator import Observation


Row = dict[str, str]
Record = dict[str, Any]
ALPACA_FIELDS = {'instruction', 'input', 'output'}


def decision_row(observation: Observation, output: str) -> Row:
    """One supervised decision: canonical messages as JSON in `instruction`, action in `output`."""
    return {'instruction': json.dumps(render_observation(observation), sort_keys=True,
                                      ensure_ascii=False, separators=(',', ':')),
            'input': '', 'output': output}


def require_alpaca_row(row: object) -> Row:
    if (not isinstance(row, dict) or set(row) != ALPACA_FIELDS or
            any(not isinstance(value, str) for value in row.values()) or row['input'] != '' or
            not row['instruction'].strip()):
        raise ValueError('invalid_schema')
    return row


def row_hash(row: Row) -> str:
    return canonical_json_sha256(row)
