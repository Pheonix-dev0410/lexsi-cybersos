import importlib
import platform
import shutil
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from cybersos.data.diagnostic_scenarios import load_diagnostic_scenarios
from cybersos.evaluation.dependency_check import check_installed_requirements
from cybersos.evaluation.environment_provenance import vendor_commits
from cybersos.evaluation.measured_model_policy import MeasuredModelPolicy
from cybersos.evaluation.model_load_check import check_in_fresh_process
from cybersos.evaluation.serialization_checks import check_serialization
from cybersos.playbooks import load_project_registry
from cybersos.policy import ServingContract, load_serving_contract
from cybersos.project_paths import DIAGNOSTIC_CASES_PATH, PROJECT_ROOT
from cybersos.safety import parse_action
from cybersos.serialization import read_json, write_json
from cybersos.simulator import RecoveryEnvironment

STAGE_IMPORTS = {
    'data': ('cybersos', 'yaml', 'curatorkit', 'auditkit'),
    'inference': ('cybersos', 'yaml', 'torch', 'transformers'),
    'align': ('cybersos', 'yaml', 'torch', 'transformers', 'peft', 'trl', 'aligntune'),
    'agent': ('cybersos', 'yaml', 'torch', 'transformers', 'peft', 'trl', 'agenttune', 'auditkit'),
}
REPORTED_PACKAGES = ('cybersos', 'pyyaml', 'pytest', 'torch', 'transformers', 'peft', 'trl',
                     'curatorkit', 'auditkit', 'aligntune', 'agenttune', 'gradio')


def check_environment(stage: str, contract_path: Path, output: Path, *,
                      base_manifest: Path | None = None, adapter: Path | None = None) -> dict[str, Any]:
    if stage not in STAGE_IMPORTS:
        raise ValueError(f'Unknown environment stage: {stage}')
    failures: list[str] = []
    imports = _import_checks(stage, failures)
    if sys.version_info[:2] != (3, 12):
        failures.append('Python 3.12 is required')
    requirements = check_installed_requirements()
    if requirements['status'] != 'passed':
        failures.append(f'Dependency check failed ({requirements["method"]}): {requirements["output"]}')
    cuda = _cuda_report()
    if stage != 'data' and not cuda['available']:
        failures.append('CUDA is not visible; this stage requires the frozen GPU runtime')
    contract, serialization, model_access = _check_contract_and_model_access(stage, contract_path, base_manifest, failures)
    generation: dict[str, object] = {'status': 'not run'}
    reload: dict[str, object] = {'status': 'not run; supply --adapter for training stages'}
    if stage != 'data' and not failures and contract is not None:
        try:
            serialization, generation, reload = _model_checks(contract, contract_path, output, stage,
                                                              base_manifest, adapter, failures)
            model_access['status'] = 'passed: model and tokenizer loaded'
        except Exception as error:
            failures.append(f'Model access/generation: {type(error).__name__}: {error}')
    if stage in {'align', 'agent'} and adapter is None:
        failures.append('Adapter reload is unverified; supply --adapter after the smoke run')
    result = {'stage': stage, 'status': 'failed' if failures else 'passed', 'python': sys.version,
              'platform': platform.platform(), 'packages': _package_versions(), 'imports': imports,
              'dependency_check': requirements, 'cuda': cuda, 'model_access': model_access,
              'serialization': serialization, 'generation': generation, 'adapter_reload': reload,
              'vendor_commits': vendor_commits(), 'failures': failures}
    write_json(output / f'doctor-{stage}.json', result)
    return result


def _package_versions() -> dict[str, str]:
    versions = {}
    for name in REPORTED_PACKAGES:
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            versions[name] = 'not installed'
    return versions


def _import_checks(stage: str, failures: list[str]) -> dict[str, str]:
    imports = {}
    for name in STAGE_IMPORTS[stage]:
        try:
            importlib.import_module(name)
            imports[name] = 'passed'
        except Exception as error:
            imports[name] = f'{type(error).__name__}: {error}'
            failures.append(f'Required import {name}: {imports[name]}')
    return imports


def _cuda_report() -> dict[str, Any]:
    cuda: dict[str, Any] = {'available': False, 'device_count': 0, 'details': 'torch not installed'}
    try:
        import torch
        cuda = {'available': torch.cuda.is_available(), 'device_count': torch.cuda.device_count(),
                'torch_cuda': torch.version.cuda,
                'devices': [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]}
    except Exception as error:
        cuda['details'] = f'{type(error).__name__}: {error}'
    if shutil.which('nvidia-smi'):
        driver = subprocess.run(['nvidia-smi', '--query-gpu=name,driver_version,memory.total', '--format=csv'],
                                capture_output=True, text=True, check=False, timeout=10)
        cuda['driver_report'] = (driver.stdout + driver.stderr).strip()
    else:
        cuda['driver_report'] = 'nvidia-smi unavailable'
    return cuda


def _check_contract_and_model_access(stage: str, contract_path: Path, base_manifest: Path | None, failures: list[str]
                     ) -> tuple[ServingContract | None, dict[str, object], dict[str, Any]]:
    model_access: dict[str, Any] = {'status': 'not verified', 'manifest': str(base_manifest) if base_manifest else None,
                                    'detail': 'No model access claim is made from credentials alone'}
    try:
        contract = load_serving_contract(contract_path)
        serialization = check_serialization(contract)
        model_access['resolved_revision'] = contract.fields['base_model']['revision']
        if base_manifest is not None:
            model_access['local_snapshot_exists'] = Path(read_json(base_manifest)['local_path']).is_dir()
        if stage != 'data':
            contract.validate_implementation(root=PROJECT_ROOT, require_resolved=True)
        return contract, serialization, model_access
    except Exception as error:
        failures.append(f'Contract/serialization: {type(error).__name__}: {error}')
        return None, {'status': 'not run'}, model_access


def _model_checks(contract: ServingContract, contract_path: Path, output: Path, stage: str,
                  base_manifest: Path | None, adapter: Path | None, failures: list[str]
                  ) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    model = MeasuredModelPolicy(contract, root=PROJECT_ROOT, base_manifest=base_manifest, adapter_path=adapter)
    model.load_for_check()
    serialization = check_serialization(contract, model.tokenizer)
    case = load_diagnostic_scenarios(DIAGNOSTIC_CASES_PATH)[0]
    env = RecoveryEnvironment(case.scenario, load_project_registry(), episode_id='doctor-generation')
    parsed = parse_action(model(env.observation()))
    generation = {'status': 'passed' if parsed.action else 'failed: malformed action',
                  'precision': contract.fields['numerics']['precision'], 'counters': model.counters}
    if parsed.action is None:
        failures.append('Short generation did not produce the required action schema')
    if adapter is None:
        return serialization, generation, {'status': 'not run; supply --adapter for training stages'}
    loaded_identity = model.identity.as_dict()
    del model
    import torch
    torch.cuda.empty_cache()
    reload = check_in_fresh_process(contract_path, output / f'doctor-{stage}-reload.json',
                                    adapter=adapter, base_manifest=base_manifest)
    if reload['identity'] != loaded_identity:
        raise ValueError('Reloaded adapter identity differs')
    return serialization, generation, reload
