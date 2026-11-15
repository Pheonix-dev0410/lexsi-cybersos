from dataclasses import dataclass
from pathlib import Path

from cybersos.serialization import write_json


@dataclass(frozen=True)
class ArtifactRequirement:
    name: str
    patterns: tuple[str, ...]
    evidence: str = 'local artifact presence only; contents require review'
    optional: bool = False


REQUIRED_ARTIFACTS = (
    ArtifactRequirement('Registered team and matching email evidence', ('submission/team.json',)),
    ArtifactRequirement('Track selection matches completed work', ('submission/track.md',)),
    ArtifactRequirement('Abstract and limit check', ('submission/abstract.md',)),
    ArtifactRequirement('Public model collection logged-out check', ('submission/model_collection_check.json',)),
    ArtifactRequirement('Public dataset collection logged-out check', ('submission/dataset_collection_check.json',)),
    ArtifactRequirement('SFT adapter weights', ('runs/sft-adapter/adapter_model.safetensors',
                                              'runs/sft-adapter/adapter_model.bin')),
    ArtifactRequirement('SFT loading instructions and model card', ('runs/sft-adapter/README.md',)),
    ArtifactRequirement('Portable base dependency and revision', ('configs/base_model.json',)),
    ArtifactRequirement('Tokenizer artifact', ('runs/sft-adapter/tokenizer_config.json',)),
    ArtifactRequirement('Dataset card and synthetic-data limitations', ('data/README.md',
                                                                      'data/curated/train/dataset_card.md')),
    ArtifactRequirement('Authored train split', ('data/scenarios/train.jsonl',)),
    ArtifactRequirement('Independent benchmark test split', ('data/scenarios/test.jsonl',)),
    ArtifactRequirement('Source manifest', ('data/sources.yaml',)),
    ArtifactRequirement('Curation provenance report', ('reports/curation_manifest.json', 'reports/curation_report.json',
                                                      'data/curated/train/curation_manifest.json')),
    ArtifactRequirement('Frozen split hashes', ('data/scenarios/manifest.json',)),
    ArtifactRequirement('Reproduction commands', ('docs/evaluation_api.md',)),
    ArtifactRequirement('Environment versions', ('reports/doctor-data.json',)),
    ArtifactRequirement('Measured before/after article or README', ('submission/article.md',)),
    ArtifactRequirement('Q/R results and diagnostic decision', ('reports/preflight.md',)),
    ArtifactRequirement('B0 intended-weight and serving-contract evidence', ('reports/runs/test/B0-*/manifest.json',)),
    ArtifactRequirement('B1 intended-weight and serving-contract evidence', ('reports/runs/test/B1-*/manifest.json',)),
    ArtifactRequirement('AgentTune incremental contribution or skip reason', ('reports/sft_residuals.md',)),
    ArtifactRequirement('Policy improvement separated from runtime enforcement', ('submission/contribution.md',)),
    ArtifactRequirement('Observation modes and language claims review', ('submission/observation_claims.md',)),
    ArtifactRequirement('Simulated restoration versus handoff versus real recovery review', ('submission/outcome_claims.md',)),
    ArtifactRequirement('Raw synthetic final traces', ('reports/runs/test/*/traces.jsonl',)),
    ArtifactRequirement('Final measured metrics and error counts', ('reports/results.json',)),
    ArtifactRequirement('Independent recorded scoring', ('reports/runs/test/*/auditkit.json',)),
    ArtifactRequirement('Compute logs and cost assumptions', ('submission/compute_and_cost.md',)),
    ArtifactRequirement('Privacy and source-rights review evidence', ('submission/privacy_review.md',)),
    ArtifactRequirement('Public demo/repository logged-out accessibility check', ('submission/public_demo_check.json',)),
    ArtifactRequirement('Submitted form receipt', ('submission/receipt.pdf', 'submission/receipt.png',
                                                 'submission/receipt.json')),
    ArtifactRequirement('Agent adapter if completed', ('runs/agent-adapter/adapter_model.safetensors',
                                                     'runs/agent-adapter/adapter_model.bin'), optional=True),
)


def check_submission(root: Path, output: Path) -> dict[str, object]:
    if not root.is_dir():
        raise ValueError(f'Project root does not exist: {root}')
    rows = []
    for requirement in REQUIRED_ARTIFACTS:
        matches = sorted({str(path.relative_to(root)) for pattern in requirement.patterns
                          for path in root.glob(pattern) if path.is_file() and path.stat().st_size > 0})
        rows.append({'artifact': requirement.name, 'status': 'exists' if matches else 'missing',
                     'optional': requirement.optional, 'paths': matches, 'expected': requirement.patterns,
                     'evidence': requirement.evidence})
    missing = sum(row['status'] == 'missing' and not row['optional'] for row in rows)
    result = {'scope': 'Section 18 local inventory; existence does not establish a passed review or public access',
              'required_missing': missing, 'artifacts': rows}
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / 'submission_inventory.json', result)
    table = ['CyberSOS submission artifact inventory', result['scope'],
             '| Artifact | Required | Status | Paths / expected location |', '| --- | --- | --- | --- |']
    for row in rows:
        paths = row['paths'] or row['expected']
        table.append(f'| {row["artifact"]} | {not row["optional"]} | {row["status"]} | {", ".join(paths)} |')
    table.append(f'\nMissing required artifacts: {missing}')
    (output / 'submission_inventory.md').write_text('\n\n'.join(table[:2]) + '\n\n' + '\n'.join(table[2:]) + '\n')
    return result
