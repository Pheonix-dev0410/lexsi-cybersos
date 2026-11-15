import platform
import subprocess
import sys
from importlib.metadata import distributions

from cybersos.project_paths import PROJECT_ROOT

VENDORED_PROJECTS = ('CuratorKIT', 'aligntune', 'AgentTune', 'AuditKIT')


def environment_versions() -> dict[str, object]:
    return {'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(),
            'packages': sorted(f'{dist.metadata["Name"]}=={dist.version}' for dist in distributions())}


def vendor_commits() -> dict[str, str]:
    result = {}
    for name in VENDORED_PROJECTS:
        process = subprocess.run(['git', '-C', str(PROJECT_ROOT / 'vendor' / name), 'rev-parse', 'HEAD'],
                                 capture_output=True, text=True, timeout=10, check=False)
        result[name] = process.stdout.strip() if not process.returncode else 'unavailable'
    return result
