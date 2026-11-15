from pathlib import Path

from cybersos.app.app_assets import AppAssets
from cybersos.app.demo_cases import DEMO_TEMPLATE_ID
from cybersos.app.evidence_content import EvidenceFiles, is_public_trace_file
from cybersos.policy import MODEL_ID
from cybersos.project_paths import DIAGNOSTIC_CASES_PATH, PLAYBOOKS_PATH, SERVING_CONTRACT_PATH, SOURCES_PATH
from cybersos.serialization import file_sha256


def about_content(assets: AppAssets) -> str:
    checked = max(source.checked_on for source in assets.registry.sources.values())
    return (
        'CyberSOS helps plan recovery for personal Google accounts and Android devices. '
        'Organization and supervised accounts are handed to the appropriate provider or administrator.\n\n'
        'Incident guidance never connects to or changes an account. Results are user-reported. '
        'Practice and saved Evidence runs use deterministic synthetic profiles and provider responses; '
        'simulated restoration does not establish real recovery. Official review remains pending.\n\n'
        'No free-text intake, uploads, account identifiers, passwords or verification values are needed. '
        'Incident state stays in server memory. Active state expires after 30 minutes of inactivity; '
        'closed sessions expire within one hour. Clear this session discards its state immediately. '
        'No incident transcript is written to an artifact.\n\n'
        f'Model target: {MODEL_ID}. The Incident guidance panel identifies the policy actually serving. '
        'The default is the R rule planner with no model checkpoint. Missing trained runs are “not run”. '
        'Structured availability intake is supported; raw-language intake: not run.\n\n'
        f'Sources checked: {checked}.\nSource registry SHA256: {file_sha256(SOURCES_PATH)}\n'
        f'Playbook SHA256: {file_sha256(PLAYBOOKS_PATH)}\n'
        f'Diagnostic data SHA256: {file_sha256(DIAGNOSTIC_CASES_PATH)}\n'
        f'Synthetic public demo definition: {DEMO_TEMPLATE_ID}. Downloadable artifacts are listed below.'
    )


def artifact_paths(assets: AppAssets, files: EvidenceFiles) -> list[str]:
    traces = [path for path in (files.baseline, files.trained)
              if path is not None and path.is_file() and is_public_trace_file(assets, path)]
    candidates: list[Path | None] = [*traces, files.report, SOURCES_PATH, PLAYBOOKS_PATH, SERVING_CONTRACT_PATH]
    return [str(path.resolve()) for path in candidates if path is not None and path.is_file()]
