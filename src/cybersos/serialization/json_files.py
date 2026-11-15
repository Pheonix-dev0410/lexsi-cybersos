import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from cybersos.serialization.json_values import to_json_value


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text())


def write_json(path: str | Path, value: object) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(to_json_value(value), sort_keys=True, ensure_ascii=False,
                                      indent=2) + '\n')


def read_jsonl(path: str | Path) -> list[Any]:
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def write_jsonl(path: str | Path, rows: Iterable[object]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Key order is preserved (no sort_keys): fact revision order must survive a round trip.
    destination.write_text(''.join(_line(row) for row in rows))


def append_jsonl(path: str | Path, rows: Iterable[object]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('a') as stream:
        stream.writelines(_line(row) for row in rows)


def _line(row: object) -> str:
    return json.dumps(to_json_value(row), ensure_ascii=False) + '\n'
