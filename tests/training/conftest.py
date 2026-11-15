import pytest

from cybersos.data.serving_budgets import ServingBudgets
from cybersos.domain import Scenario


@pytest.fixture
def budgets() -> ServingBudgets:
    """Contract-shaped budgets sized for the one-id-per-character test tokenizer."""
    return ServingBudgets(actions=12, prompt_tokens=60000, context_tokens=61000,
                          generation_tokens=400, sequence_tokens=400000)


@pytest.fixture
def scenario() -> Scenario:
    facts = dict(account_owner=True, organization_managed=False, child_account=False,
                 safe_other_device=True, password_known=True, backup_code_exists=True,
                 backup_code_accessible_now=True, independent_passkey_exists=False,
                 enrolled_security_key_exists=False, alternate_number_exists=False,
                 recovery_email_exists=False)
    return Scenario.from_mapping({
        'scenario_id': 'server-only-scenario', 'provider': 'google_personal', 'account_owner': True,
        'incident': 'lost_phone', 'opening_message': 'I lost my phone and need my own account.',
        'access': facts, 'initial_facts': facts,
        'objective': 'simulated_access_restored',
        'provider_script': {'use_accessible_backup_code': 'success'},
    })
