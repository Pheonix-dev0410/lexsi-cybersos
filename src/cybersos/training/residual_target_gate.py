import re
from pathlib import Path


def require_residual_target(path: str | Path) -> str:
    source = Path(path)
    if not source.is_file():
        raise ValueError('AgentTune not run: reports/sft_residuals.md must name a sequential target')
    report = source.read_text()
    match = re.search(r'^\s*(?:\*\*)?(?:AgentTune target|Sequential target|Target)(?:\*\*)?:\s*(.+)',
                      report, re.IGNORECASE | re.MULTILINE)
    if match is None:
        raise ValueError('AgentTune not run: residual report needs a Target: line')
    target = match.group(1).strip().strip('*').strip()
    if (len(target) < 12 or target.lower() in {'none', 'tbd', 'todo', 'not run'} or
            any(word in target.lower() for word in ('formatting only', 'source-rule only', 'ui only'))):
        raise ValueError('AgentTune not run: no meaningful sequential target recorded')
    return target
