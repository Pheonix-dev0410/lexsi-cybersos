from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / 'data'
CONFIGS_DIR = PROJECT_ROOT / 'configs'
REPORTS_DIR = PROJECT_ROOT / 'reports'
SOURCES_PATH = DATA_DIR / 'sources.yaml'
PLAYBOOKS_PATH = DATA_DIR / 'playbooks.yaml'
SCENARIOS_DIR = DATA_DIR / 'scenarios'
DIAGNOSTIC_CASES_PATH = SCENARIOS_DIR / 'diagnostic.jsonl'
SERVING_CONTRACT_PATH = CONFIGS_DIR / 'baselines.yaml'
