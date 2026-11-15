import importlib.util
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, distributions, version


def check_installed_requirements() -> dict[str, object]:
    """Run `pip check` when pip exists; uv-created environments ship without it, so fall back to metadata."""
    if importlib.util.find_spec('pip') is not None:
        process = subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True,
                                 text=True, check=False, timeout=30)
        return {'method': 'pip check', 'status': 'passed' if process.returncode == 0 else 'failed',
                'output': (process.stdout + process.stderr).strip()}
    problems = sorted({problem for dist in distributions() for problem in _unmet(dist.metadata['Name'],
                                                                                dist.requires or ())})
    return {'method': 'importlib.metadata requirement check',
            'status': 'failed' if problems else 'passed', 'output': '\n'.join(problems)}


def _unmet(name: str, requirements: list[str] | tuple[str, ...]) -> list[str]:
    from packaging.requirements import InvalidRequirement, Requirement

    problems = []
    for text in requirements:
        try:
            requirement = Requirement(text)
        except InvalidRequirement:
            continue
        if requirement.marker is not None and not requirement.marker.evaluate({'extra': ''}):
            continue
        try:
            installed = version(requirement.name)
        except PackageNotFoundError:
            problems.append(f'{name} requires {requirement}, which is not installed')
            continue
        if not requirement.specifier.contains(installed, prereleases=True):
            problems.append(f'{name} requires {requirement}, but {installed} is installed')
    return problems
