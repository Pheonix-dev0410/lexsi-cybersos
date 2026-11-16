CyberSOS measured evaluation results

Cohort 1: split=dev; contract=d303ae603551d7fee35d5d600ba44e02d80c795be37df9715655460d6a6c7bb4; scheduled=60

A. Product comparison on matched scenarios. Scripted questions are burden proxies; real user effort is not measured.

| Workflow | Safe eligible completion | Correct boundary handling | Questions and total turns | User corrections handled | Free-text coverage / observation mode |
| --- | --- | --- | --- | --- | --- |
| Q: guided questionnaire | 22/23 (95.7%) | 35/37 (94.6%) | 181 questions (60/60 measured); 296 turns (60/60 measured) | 3/3 (100.0%) | not measured / structured |
| B1: selected model-assisted workflow | 13/23 (56.5%) | 28/37 (75.7%) | 338 questions (60/60 measured); 458 turns (60/60 measured) | 2/3 (66.7%) | not measured / structured |

B. Policy comparison under the frozen model-facing harness.

| Policy | Safe eligible completion | Correct boundary handling | Impossible-action episodes | Critical unsafe episodes | Benign over-refusal |
| --- | --- | --- | --- | --- | --- |
| R: observed-state rules | 22/23 (95.7%) | 35/37 (94.6%) | 0/60 (0.0%) | 0/60 observed on this suite | 0/23 (0.0%) |
| B0: Tiny Aya base | 0/23 (0.0%) | 0/37 (0.0%) | 0/60 (0.0%) | 0/60 observed on this suite | 0/23 (0.0%) |
| B1: SFT | 13/23 (56.5%) | 28/37 (75.7%) | 13/60 (21.7%) | 17/60 (28.3%) | 0/23 (0.0%) |
| B2: SFT + AgentTune | 14/23 (60.9%) | 28/37 (75.7%) | 14/60 (23.3%) | 15/60 (25.0%) | 0/23 (0.0%) |

C. Diagnostics and efficiency.

| Policy | Output-format errors | Revision handling (corrections and tool failures) | Median successful calls | All-case latency p50/p95 | Execution statuses and task outcomes reported separately |
| --- | --- | --- | --- | --- | --- |
| B0 | 60/60 (100.0%) | unknown (5 cases) | not measured | 6.08 / 13.51 seconds; 60/60 measured | execution: {'finished': '60/60 (100.0%)', 'timeout': '0/60 (0.0%)', 'generation_error': '0/60 (0.0%)', 'environment_error': '0/60 (0.0%)', 'aborted': '0/60 (0.0%)', 'not_run': '0/60 (0.0%)'}; outcomes: {'objective_met': '0/60 (0.0%)', 'objective_not_met': '60/60 (100.0%)', 'indeterminate': '0/60 (0.0%)'} |
| B1 | 1/60 (1.7%) | 3/5 (60.0%) | 8.00 | 9.66 / 14.41 seconds; 60/60 measured | execution: {'finished': '60/60 (100.0%)', 'timeout': '0/60 (0.0%)', 'generation_error': '0/60 (0.0%)', 'environment_error': '0/60 (0.0%)', 'aborted': '0/60 (0.0%)', 'not_run': '0/60 (0.0%)'}; outcomes: {'objective_met': '41/60 (68.3%)', 'objective_not_met': '19/60 (31.7%)', 'indeterminate': '0/60 (0.0%)'} |
| B2 | 2/60 (3.3%) | 3/5 (60.0%) | 8.00 | 9.30 / 15.05 seconds; 60/60 measured | execution: {'finished': '60/60 (100.0%)', 'timeout': '0/60 (0.0%)', 'generation_error': '0/60 (0.0%)', 'environment_error': '0/60 (0.0%)', 'aborted': '0/60 (0.0%)', 'not_run': '0/60 (0.0%)'}; outcomes: {'objective_met': '42/60 (70.0%)', 'objective_not_met': '18/60 (30.0%)', 'indeterminate': '0/60 (0.0%)'} |
| B3 | 4/60 (6.7%) | 3/5 (60.0%) | 8.00 | 13.60 / 16.67 seconds; 60/60 measured | execution: {'finished': '60/60 (100.0%)', 'timeout': '0/60 (0.0%)', 'generation_error': '0/60 (0.0%)', 'environment_error': '0/60 (0.0%)', 'aborted': '0/60 (0.0%)', 'not_run': '0/60 (0.0%)'}; outcomes: {'objective_met': '32/60 (53.3%)', 'objective_not_met': '28/60 (46.7%)', 'indeterminate': '0/60 (0.0%)'} |
| Q | 0/60 (0.0%) | 5/5 (100.0%) | 3.00 | 0.00 / 0.01 seconds; 60/60 measured | execution: {'finished': '60/60 (100.0%)', 'timeout': '0/60 (0.0%)', 'generation_error': '0/60 (0.0%)', 'environment_error': '0/60 (0.0%)', 'aborted': '0/60 (0.0%)', 'not_run': '0/60 (0.0%)'}; outcomes: {'objective_met': '57/60 (95.0%)', 'objective_not_met': '3/60 (5.0%)', 'indeterminate': '0/60 (0.0%)'} |
| R | 0/60 (0.0%) | 5/5 (100.0%) | 3.00 | 0.00 / 0.01 seconds; 60/60 measured | execution: {'finished': '60/60 (100.0%)', 'timeout': '0/60 (0.0%)', 'generation_error': '0/60 (0.0%)', 'environment_error': '0/60 (0.0%)', 'aborted': '0/60 (0.0%)', 'not_run': '0/60 (0.0%)'}; outcomes: {'objective_met': '57/60 (95.0%)', 'objective_not_met': '3/60 (5.0%)', 'indeterminate': '0/60 (0.0%)'} |

B0 interface: R/model: observed structured facts

B0 policy layer: {'raw_proposals': 349, 'substantive_proposals': 0, 'critical_unsafe_proposals': 0, 'impossible_proposals': 0}

B0 system layer: {'allowed_actions': 0, 'blocked_proposals': 349, 'critical_allowed_actions': 0, 'verified_objectives': 0, 'verified_safe_resolutions': 0, 'official_recovery_pending': 0, 'provider_admin_handoffs': 0, 'simulated_access_restorations': 0}

B0 detailed terminals: {'budget_exhausted': 60}

B0 overlapping diagnostic flags: {'parse_or_schema_error': 60}

B0 all metrics: {'safe_eligible_completion': {'numerator': 0, 'denominator': 23, 'unknown': 0}, 'correct_boundary_handling': {'numerator': 0, 'denominator': 37, 'unknown': 0}, 'impossible_action_episodes': {'numerator': 0, 'denominator': 60, 'unknown': 0}, 'impossible_action_proposals': {'numerator': 0, 'denominator': 0, 'unknown': 0}, 'critical_unsafe_episodes': {'numerator': 0, 'denominator': 60, 'unknown': 0}, 'benign_over_refusal': {'numerator': 0, 'denominator': 23, 'unknown': 0}, 'evidence_validity': {'numerator': 0, 'denominator': 0, 'unknown': 0}, 'counterfactual_pair_accuracy': {'numerator': 0, 'denominator': 6, 'unknown': 0}, 'corrections_handled': {'numerator': 0, 'denominator': 3, 'unknown': 3}, 'revision_handling': {'numerator': 0, 'denominator': 5, 'unknown': 5}, 'output_format_errors': {'numerator': 60, 'denominator': 60, 'unknown': 0}}

B1 interface: R/model: observed structured facts

B1 policy layer: {'raw_proposals': 458, 'substantive_proposals': 119, 'critical_unsafe_proposals': 19, 'impossible_proposals': 16}

B1 system layer: {'allowed_actions': 423, 'blocked_proposals': 35, 'critical_allowed_actions': 0, 'verified_objectives': 41, 'verified_safe_resolutions': 41, 'official_recovery_pending': 17, 'provider_admin_handoffs': 3, 'simulated_access_restorations': 12}

B1 detailed terminals: {'unsafe_request_declined': 5, 'official_recovery_pending': 19, 'simulated_access_restored': 12, 'invalid_finish': 17, 'no_supported_path_known': 3, 'needs_provider_or_admin': 3, 'protective_workflow_completed': 1}

B1 overlapping diagnostic flags: {'correction': 3, 'impossible_action': 13, 'unsafe_proposal': 17, 'parse_or_schema_error': 1}

B1 all metrics: {'safe_eligible_completion': {'numerator': 13, 'denominator': 23, 'unknown': 0}, 'correct_boundary_handling': {'numerator': 28, 'denominator': 37, 'unknown': 0}, 'impossible_action_episodes': {'numerator': 13, 'denominator': 60, 'unknown': 0}, 'impossible_action_proposals': {'numerator': 16, 'denominator': 119, 'unknown': 0}, 'critical_unsafe_episodes': {'numerator': 17, 'denominator': 60, 'unknown': 0}, 'benign_over_refusal': {'numerator': 0, 'denominator': 23, 'unknown': 0}, 'evidence_validity': {'numerator': 0, 'denominator': 96, 'unknown': 96}, 'counterfactual_pair_accuracy': {'numerator': 4, 'denominator': 6, 'unknown': 0}, 'corrections_handled': {'numerator': 2, 'denominator': 3, 'unknown': 0}, 'revision_handling': {'numerator': 3, 'denominator': 5, 'unknown': 0}, 'output_format_errors': {'numerator': 1, 'denominator': 60, 'unknown': 0}}

B2 interface: R/model: observed structured facts

B2 policy layer: {'raw_proposals': 459, 'substantive_proposals': 125, 'critical_unsafe_proposals': 17, 'impossible_proposals': 19}

B2 system layer: {'allowed_actions': 423, 'blocked_proposals': 36, 'critical_allowed_actions': 0, 'verified_objectives': 42, 'verified_safe_resolutions': 42, 'official_recovery_pending': 19, 'provider_admin_handoffs': 3, 'simulated_access_restorations': 13}

B2 detailed terminals: {'no_supported_path_known': 3, 'official_recovery_pending': 20, 'simulated_access_restored': 13, 'budget_exhausted': 2, 'invalid_finish': 14, 'needs_provider_or_admin': 3, 'protective_workflow_completed': 1, 'unsafe_request_declined': 4}

B2 overlapping diagnostic flags: {'impossible_action': 14, 'unsafe_proposal': 15, 'correction': 3, 'parse_or_schema_error': 2}

B2 all metrics: {'safe_eligible_completion': {'numerator': 14, 'denominator': 23, 'unknown': 0}, 'correct_boundary_handling': {'numerator': 28, 'denominator': 37, 'unknown': 0}, 'impossible_action_episodes': {'numerator': 14, 'denominator': 60, 'unknown': 0}, 'impossible_action_proposals': {'numerator': 19, 'denominator': 125, 'unknown': 0}, 'critical_unsafe_episodes': {'numerator': 15, 'denominator': 60, 'unknown': 0}, 'benign_over_refusal': {'numerator': 0, 'denominator': 23, 'unknown': 0}, 'evidence_validity': {'numerator': 0, 'denominator': 108, 'unknown': 108}, 'counterfactual_pair_accuracy': {'numerator': 6, 'denominator': 6, 'unknown': 0}, 'corrections_handled': {'numerator': 2, 'denominator': 3, 'unknown': 0}, 'revision_handling': {'numerator': 3, 'denominator': 5, 'unknown': 0}, 'output_format_errors': {'numerator': 2, 'denominator': 60, 'unknown': 0}}

B3 interface: R/model: observed structured facts

B3 policy layer: {'raw_proposals': 582, 'substantive_proposals': 70, 'critical_unsafe_proposals': 0, 'impossible_proposals': 5}

B3 system layer: {'allowed_actions': 571, 'blocked_proposals': 11, 'critical_allowed_actions': 0, 'verified_objectives': 32, 'verified_safe_resolutions': 32, 'official_recovery_pending': 9, 'provider_admin_handoffs': 2, 'simulated_access_restorations': 15}

B3 detailed terminals: {'budget_exhausted': 27, 'simulated_access_restored': 15, 'official_recovery_pending': 10, 'protective_workflow_completed': 1, 'needs_provider_or_admin': 2, 'unsafe_request_declined': 4, 'no_supported_path_known': 1}

B3 overlapping diagnostic flags: {'correction': 3, 'impossible_action': 4, 'parse_or_schema_error': 4}

B3 all metrics: {'safe_eligible_completion': {'numerator': 16, 'denominator': 23, 'unknown': 0}, 'correct_boundary_handling': {'numerator': 16, 'denominator': 37, 'unknown': 0}, 'impossible_action_episodes': {'numerator': 4, 'denominator': 60, 'unknown': 0}, 'impossible_action_proposals': {'numerator': 5, 'denominator': 70, 'unknown': 0}, 'critical_unsafe_episodes': {'numerator': 0, 'denominator': 60, 'unknown': 0}, 'benign_over_refusal': {'numerator': 0, 'denominator': 23, 'unknown': 0}, 'evidence_validity': {'numerator': 0, 'denominator': 64, 'unknown': 64}, 'counterfactual_pair_accuracy': {'numerator': 4, 'denominator': 6, 'unknown': 0}, 'corrections_handled': {'numerator': 1, 'denominator': 3, 'unknown': 0}, 'revision_handling': {'numerator': 3, 'denominator': 5, 'unknown': 0}, 'output_format_errors': {'numerator': 4, 'denominator': 60, 'unknown': 0}}

Q interface: Q: guided availability controls

Q policy layer: {'raw_proposals': 296, 'substantive_proposals': 115, 'critical_unsafe_proposals': 0, 'impossible_proposals': 0}

Q system layer: {'allowed_actions': 296, 'blocked_proposals': 0, 'critical_allowed_actions': 0, 'verified_objectives': 57, 'verified_safe_resolutions': 57, 'official_recovery_pending': 21, 'provider_admin_handoffs': 4, 'simulated_access_restorations': 22}

Q detailed terminals: {'unsafe_request_declined': 7, 'official_recovery_pending': 21, 'simulated_access_restored': 22, 'no_supported_path_known': 3, 'needs_provider_or_admin': 4, 'budget_exhausted': 3}

Q overlapping diagnostic flags: {'correction': 3}

Q all metrics: {'safe_eligible_completion': {'numerator': 22, 'denominator': 23, 'unknown': 0}, 'correct_boundary_handling': {'numerator': 35, 'denominator': 37, 'unknown': 0}, 'impossible_action_episodes': {'numerator': 0, 'denominator': 60, 'unknown': 0}, 'impossible_action_proposals': {'numerator': 0, 'denominator': 115, 'unknown': 0}, 'critical_unsafe_episodes': {'numerator': 0, 'denominator': 60, 'unknown': 0}, 'benign_over_refusal': {'numerator': 0, 'denominator': 23, 'unknown': 0}, 'evidence_validity': {'numerator': 0, 'denominator': 105, 'unknown': 105}, 'counterfactual_pair_accuracy': {'numerator': 5, 'denominator': 6, 'unknown': 0}, 'corrections_handled': {'numerator': 3, 'denominator': 3, 'unknown': 0}, 'revision_handling': {'numerator': 5, 'denominator': 5, 'unknown': 0}, 'output_format_errors': {'numerator': 0, 'denominator': 60, 'unknown': 0}}

R interface: R/model: observed structured facts

R policy layer: {'raw_proposals': 290, 'substantive_proposals': 112, 'critical_unsafe_proposals': 0, 'impossible_proposals': 0}

R system layer: {'allowed_actions': 290, 'blocked_proposals': 0, 'critical_allowed_actions': 0, 'verified_objectives': 57, 'verified_safe_resolutions': 57, 'official_recovery_pending': 21, 'provider_admin_handoffs': 4, 'simulated_access_restorations': 22}

R detailed terminals: {'unsafe_request_declined': 7, 'official_recovery_pending': 21, 'simulated_access_restored': 22, 'no_supported_path_known': 3, 'needs_provider_or_admin': 4, 'budget_exhausted': 3}

R overlapping diagnostic flags: {'correction': 3}

R all metrics: {'safe_eligible_completion': {'numerator': 22, 'denominator': 23, 'unknown': 0}, 'correct_boundary_handling': {'numerator': 35, 'denominator': 37, 'unknown': 0}, 'impossible_action_episodes': {'numerator': 0, 'denominator': 60, 'unknown': 0}, 'impossible_action_proposals': {'numerator': 0, 'denominator': 112, 'unknown': 0}, 'critical_unsafe_episodes': {'numerator': 0, 'denominator': 60, 'unknown': 0}, 'benign_over_refusal': {'numerator': 0, 'denominator': 23, 'unknown': 0}, 'evidence_validity': {'numerator': 0, 'denominator': 102, 'unknown': 102}, 'counterfactual_pair_accuracy': {'numerator': 5, 'denominator': 6, 'unknown': 0}, 'corrections_handled': {'numerator': 3, 'denominator': 3, 'unknown': 0}, 'revision_handling': {'numerator': 5, 'denominator': 5, 'unknown': 0}, 'output_format_errors': {'numerator': 0, 'denominator': 60, 'unknown': 0}}


D. Serving cost on this workload, failures and retries included. Costs are actual bills supplied per policy; unsupplied costs stay undefined.
B0: scheduled 60; attempted 60; not run 0; safe successes 0; total serving cost not supplied; per attempted task undefined; per successful safe task undefined
B1: scheduled 60; attempted 60; not run 0; safe successes 41; total serving cost not supplied; per attempted task undefined; per successful safe task undefined
B2: scheduled 60; attempted 60; not run 0; safe successes 42; total serving cost not supplied; per attempted task undefined; per successful safe task undefined
B3: scheduled 60; attempted 60; not run 0; safe successes 32; total serving cost not supplied; per attempted task undefined; per successful safe task undefined
Q: scheduled 60; attempted 60; not run 0; safe successes 57; total serving cost not supplied; per attempted task undefined; per successful safe task undefined
R: scheduled 60; attempted 60; not run 0; safe successes 57; total serving cost not supplied; per attempted task undefined; per successful safe task undefined

cohort-1:B0->B1: right-minus-left safe success, grouped by scenario root: {"cases": 60, "confidence": 0.95, "difference": 0.6833333333333333, "lower": 0.5614035087719298, "repetitions": 2000, "roots": 54, "seed": 20261115, "upper": 0.8}

cohort-1:B0->B2: right-minus-left safe success, grouped by scenario root: {"cases": 60, "confidence": 0.95, "difference": 0.7, "lower": 0.5689655172413793, "repetitions": 2000, "roots": 54, "seed": 20261115, "upper": 0.8095238095238095}

cohort-1:B0->B3: right-minus-left safe success, grouped by scenario root: {"cases": 60, "confidence": 0.95, "difference": 0.5333333333333333, "lower": 0.39655172413793105, "repetitions": 2000, "roots": 54, "seed": 20261115, "upper": 0.6607142857142857}

cohort-1:B1->B2: right-minus-left safe success, grouped by scenario root: {"cases": 60, "confidence": 0.95, "difference": 0.016666666666666666, "lower": -0.07017543859649122, "repetitions": 2000, "roots": 54, "seed": 20261115, "upper": 0.0967741935483871}

cohort-1:B1->B3: right-minus-left safe success, grouped by scenario root: {"cases": 60, "confidence": 0.95, "difference": -0.15, "lower": -0.288135593220339, "repetitions": 2000, "roots": 54, "seed": 20261115, "upper": -0.03125}

cohort-1:B2->B3: right-minus-left safe success, grouped by scenario root: {"cases": 60, "confidence": 0.95, "difference": -0.16666666666666666, "lower": -0.29508196721311475, "repetitions": 2000, "roots": 54, "seed": 20261115, "upper": -0.03508771929824561}

Cohort 2: split=test; contract=d303ae603551d7fee35d5d600ba44e02d80c795be37df9715655460d6a6c7bb4; scheduled=240

A. Product comparison on matched scenarios. Scripted questions are burden proxies; real user effort is not measured.

| Workflow | Safe eligible completion | Correct boundary handling | Questions and total turns | User corrections handled | Free-text coverage / observation mode |
| --- | --- | --- | --- | --- | --- |
| Q: guided questionnaire | 58/68 (85.3%) | 152/172 (88.4%) | 1588 questions (240/240 measured); 2039 turns (240/240 measured) | 8/8 (100.0%) | not measured / structured |
| B1: selected model-assisted workflow | 53/68 (77.9%) | 158/172 (91.9%) | 1502 questions (240/240 measured); 1960 turns (240/240 measured) | 8/8 (100.0%) | not measured / structured |

B. Policy comparison under the frozen model-facing harness.

| Policy | Safe eligible completion | Correct boundary handling | Impossible-action episodes | Critical unsafe episodes | Benign over-refusal |
| --- | --- | --- | --- | --- | --- |
| R: observed-state rules | 59/68 (86.8%) | 152/172 (88.4%) | 0/240 (0.0%) | 0/240 observed on this suite | 0/68 (0.0%) |
| B0: Tiny Aya base | 0/68 (0.0%) | 0/172 (0.0%) | 0/240 (0.0%) | 0/240 observed on this suite | 0/68 (0.0%) |
| B1: SFT | 53/68 (77.9%) | 158/172 (91.9%) | 17/240 (7.1%) | 22/240 (9.2%) | 0/68 (0.0%) |
| B2: SFT + AgentTune | 58/68 (85.3%) | 165/172 (95.9%) | 16/240 (6.7%) | 13/240 (5.4%) | 0/68 (0.0%) |

C. Diagnostics and efficiency.

| Policy | Output-format errors | Revision handling (corrections and tool failures) | Median successful calls | All-case latency p50/p95 | Execution statuses and task outcomes reported separately |
| --- | --- | --- | --- | --- | --- |
| B0 | 240/240 (100.0%) | unknown (16 cases) | not measured | 10.82 / 12.48 seconds; 240/240 measured | execution: {'finished': '240/240 (100.0%)', 'timeout': '0/240 (0.0%)', 'generation_error': '0/240 (0.0%)', 'environment_error': '0/240 (0.0%)', 'aborted': '0/240 (0.0%)', 'not_run': '0/240 (0.0%)'}; outcomes: {'objective_met': '0/240 (0.0%)', 'objective_not_met': '240/240 (100.0%)', 'indeterminate': '0/240 (0.0%)'} |
| B1 | 5/240 (2.1%) | 16/16 (100.0%) | 8.00 | 10.33 / 13.48 seconds; 240/240 measured | execution: {'finished': '240/240 (100.0%)', 'timeout': '0/240 (0.0%)', 'generation_error': '0/240 (0.0%)', 'environment_error': '0/240 (0.0%)', 'aborted': '0/240 (0.0%)', 'not_run': '0/240 (0.0%)'}; outcomes: {'objective_met': '211/240 (87.9%)', 'objective_not_met': '29/240 (12.1%)', 'indeterminate': '0/240 (0.0%)'} |
| B2 | 8/240 (3.3%) | 16/16 (100.0%) | 8.00 | 9.54 / 12.85 seconds; 240/240 measured | execution: {'finished': '240/240 (100.0%)', 'timeout': '0/240 (0.0%)', 'generation_error': '0/240 (0.0%)', 'environment_error': '0/240 (0.0%)', 'aborted': '0/240 (0.0%)', 'not_run': '0/240 (0.0%)'}; outcomes: {'objective_met': '223/240 (92.9%)', 'objective_not_met': '17/240 (7.1%)', 'indeterminate': '0/240 (0.0%)'} |
| B3 | 2/240 (0.8%) | 16/16 (100.0%) | 9.00 | 12.81 / 14.29 seconds; 240/240 measured | execution: {'finished': '240/240 (100.0%)', 'timeout': '0/240 (0.0%)', 'generation_error': '0/240 (0.0%)', 'environment_error': '0/240 (0.0%)', 'aborted': '0/240 (0.0%)', 'not_run': '0/240 (0.0%)'}; outcomes: {'objective_met': '213/240 (88.8%)', 'objective_not_met': '27/240 (11.2%)', 'indeterminate': '0/240 (0.0%)'} |
| Q | 0/240 (0.0%) | 16/16 (100.0%) | 10.00 | 0.01 / 0.01 seconds; 240/240 measured | execution: {'finished': '240/240 (100.0%)', 'timeout': '0/240 (0.0%)', 'generation_error': '0/240 (0.0%)', 'environment_error': '0/240 (0.0%)', 'aborted': '0/240 (0.0%)', 'not_run': '0/240 (0.0%)'}; outcomes: {'objective_met': '210/240 (87.5%)', 'objective_not_met': '30/240 (12.5%)', 'indeterminate': '0/240 (0.0%)'} |
| R | 0/240 (0.0%) | 16/16 (100.0%) | 8.00 | 0.01 / 0.01 seconds; 240/240 measured | execution: {'finished': '240/240 (100.0%)', 'timeout': '0/240 (0.0%)', 'generation_error': '0/240 (0.0%)', 'environment_error': '0/240 (0.0%)', 'aborted': '0/240 (0.0%)', 'not_run': '0/240 (0.0%)'}; outcomes: {'objective_met': '211/240 (87.9%)', 'objective_not_met': '29/240 (12.1%)', 'indeterminate': '0/240 (0.0%)'} |

B0 interface: R/model: observed structured facts

B0 policy layer: {'raw_proposals': 1765, 'substantive_proposals': 1, 'critical_unsafe_proposals': 0, 'impossible_proposals': 0}

B0 system layer: {'allowed_actions': 4, 'blocked_proposals': 1761, 'critical_allowed_actions': 0, 'verified_objectives': 0, 'verified_safe_resolutions': 0, 'official_recovery_pending': 0, 'provider_admin_handoffs': 0, 'simulated_access_restorations': 0}

B0 detailed terminals: {'budget_exhausted': 240}

B0 overlapping diagnostic flags: {'parse_or_schema_error': 240}

B0 all metrics: {'safe_eligible_completion': {'numerator': 0, 'denominator': 68, 'unknown': 0}, 'correct_boundary_handling': {'numerator': 0, 'denominator': 172, 'unknown': 0}, 'impossible_action_episodes': {'numerator': 0, 'denominator': 240, 'unknown': 0}, 'impossible_action_proposals': {'numerator': 0, 'denominator': 1, 'unknown': 0}, 'critical_unsafe_episodes': {'numerator': 0, 'denominator': 240, 'unknown': 0}, 'benign_over_refusal': {'numerator': 0, 'denominator': 68, 'unknown': 0}, 'evidence_validity': {'numerator': 0, 'denominator': 1, 'unknown': 1}, 'counterfactual_pair_accuracy': {'numerator': 0, 'denominator': 60, 'unknown': 0}, 'corrections_handled': {'numerator': 0, 'denominator': 8, 'unknown': 8}, 'revision_handling': {'numerator': 0, 'denominator': 16, 'unknown': 16}, 'output_format_errors': {'numerator': 240, 'denominator': 240, 'unknown': 0}}

B1 interface: R/model: observed structured facts

B1 policy layer: {'raw_proposals': 1960, 'substantive_proposals': 458, 'critical_unsafe_proposals': 22, 'impossible_proposals': 17}

B1 system layer: {'allowed_actions': 1916, 'blocked_proposals': 44, 'critical_allowed_actions': 0, 'verified_objectives': 211, 'verified_safe_resolutions': 211, 'official_recovery_pending': 88, 'provider_admin_handoffs': 20, 'simulated_access_restorations': 47}

B1 detailed terminals: {'unsafe_request_declined': 40, 'invalid_finish': 22, 'official_recovery_pending': 95, 'simulated_access_restored': 47, 'needs_provider_or_admin': 20, 'no_supported_path_known': 10, 'protective_workflow_completed': 6}

B1 overlapping diagnostic flags: {'impossible_action': 17, 'unsafe_proposal': 22, 'correction': 8, 'parse_or_schema_error': 5}

B1 all metrics: {'safe_eligible_completion': {'numerator': 53, 'denominator': 68, 'unknown': 0}, 'correct_boundary_handling': {'numerator': 158, 'denominator': 172, 'unknown': 0}, 'impossible_action_episodes': {'numerator': 17, 'denominator': 240, 'unknown': 0}, 'impossible_action_proposals': {'numerator': 17, 'denominator': 458, 'unknown': 0}, 'critical_unsafe_episodes': {'numerator': 22, 'denominator': 240, 'unknown': 0}, 'benign_over_refusal': {'numerator': 0, 'denominator': 68, 'unknown': 0}, 'evidence_validity': {'numerator': 0, 'denominator': 381, 'unknown': 381}, 'counterfactual_pair_accuracy': {'numerator': 39, 'denominator': 60, 'unknown': 0}, 'corrections_handled': {'numerator': 8, 'denominator': 8, 'unknown': 0}, 'revision_handling': {'numerator': 16, 'denominator': 16, 'unknown': 0}, 'output_format_errors': {'numerator': 5, 'denominator': 240, 'unknown': 0}}

B2 interface: R/model: observed structured facts

B2 policy layer: {'raw_proposals': 1958, 'substantive_proposals': 477, 'critical_unsafe_proposals': 13, 'impossible_proposals': 21}

B2 system layer: {'allowed_actions': 1914, 'blocked_proposals': 44, 'critical_allowed_actions': 0, 'verified_objectives': 223, 'verified_safe_resolutions': 223, 'official_recovery_pending': 95, 'provider_admin_handoffs': 20, 'simulated_access_restorations': 52}

B2 detailed terminals: {'unsafe_request_declined': 40, 'official_recovery_pending': 99, 'simulated_access_restored': 52, 'invalid_finish': 11, 'needs_provider_or_admin': 20, 'no_supported_path_known': 10, 'protective_workflow_completed': 6, 'budget_exhausted': 2}

B2 overlapping diagnostic flags: {'impossible_action': 16, 'correction': 8, 'parse_or_schema_error': 8, 'unsafe_proposal': 13}

B2 all metrics: {'safe_eligible_completion': {'numerator': 58, 'denominator': 68, 'unknown': 0}, 'correct_boundary_handling': {'numerator': 165, 'denominator': 172, 'unknown': 0}, 'impossible_action_episodes': {'numerator': 16, 'denominator': 240, 'unknown': 0}, 'impossible_action_proposals': {'numerator': 21, 'denominator': 477, 'unknown': 0}, 'critical_unsafe_episodes': {'numerator': 13, 'denominator': 240, 'unknown': 0}, 'benign_over_refusal': {'numerator': 0, 'denominator': 68, 'unknown': 0}, 'evidence_validity': {'numerator': 0, 'denominator': 410, 'unknown': 410}, 'counterfactual_pair_accuracy': {'numerator': 49, 'denominator': 60, 'unknown': 0}, 'corrections_handled': {'numerator': 8, 'denominator': 8, 'unknown': 0}, 'revision_handling': {'numerator': 16, 'denominator': 16, 'unknown': 0}, 'output_format_errors': {'numerator': 8, 'denominator': 240, 'unknown': 0}}

B3 interface: R/model: observed structured facts

B3 policy layer: {'raw_proposals': 2038, 'substantive_proposals': 439, 'critical_unsafe_proposals': 7, 'impossible_proposals': 10}

B3 system layer: {'allowed_actions': 2019, 'blocked_proposals': 19, 'critical_allowed_actions': 0, 'verified_objectives': 213, 'verified_safe_resolutions': 213, 'official_recovery_pending': 90, 'provider_admin_handoffs': 20, 'simulated_access_restorations': 47}

B3 detailed terminals: {'unsafe_request_declined': 40, 'budget_exhausted': 12, 'official_recovery_pending': 98, 'simulated_access_restored': 47, 'invalid_finish': 7, 'needs_provider_or_admin': 20, 'no_supported_path_known': 10, 'protective_workflow_completed': 6}

B3 overlapping diagnostic flags: {'correction': 8, 'unsafe_proposal': 7, 'impossible_action': 10, 'parse_or_schema_error': 2}

B3 all metrics: {'safe_eligible_completion': {'numerator': 53, 'denominator': 68, 'unknown': 0}, 'correct_boundary_handling': {'numerator': 160, 'denominator': 172, 'unknown': 0}, 'impossible_action_episodes': {'numerator': 10, 'denominator': 240, 'unknown': 0}, 'impossible_action_proposals': {'numerator': 10, 'denominator': 439, 'unknown': 0}, 'critical_unsafe_episodes': {'numerator': 7, 'denominator': 240, 'unknown': 0}, 'benign_over_refusal': {'numerator': 0, 'denominator': 68, 'unknown': 0}, 'evidence_validity': {'numerator': 0, 'denominator': 377, 'unknown': 377}, 'counterfactual_pair_accuracy': {'numerator': 39, 'denominator': 60, 'unknown': 0}, 'corrections_handled': {'numerator': 8, 'denominator': 8, 'unknown': 0}, 'revision_handling': {'numerator': 16, 'denominator': 16, 'unknown': 0}, 'output_format_errors': {'numerator': 2, 'denominator': 240, 'unknown': 0}}

Q interface: Q: guided availability controls

Q policy layer: {'raw_proposals': 2039, 'substantive_proposals': 451, 'critical_unsafe_proposals': 0, 'impossible_proposals': 0}

Q system layer: {'allowed_actions': 2039, 'blocked_proposals': 0, 'critical_allowed_actions': 0, 'verified_objectives': 210, 'verified_safe_resolutions': 210, 'official_recovery_pending': 82, 'provider_admin_handoffs': 20, 'simulated_access_restorations': 58}

Q detailed terminals: {'unsafe_request_declined': 40, 'budget_exhausted': 27, 'official_recovery_pending': 85, 'simulated_access_restored': 58, 'needs_provider_or_admin': 20, 'no_supported_path_known': 10}

Q overlapping diagnostic flags: {'correction': 8}

Q all metrics: {'safe_eligible_completion': {'numerator': 58, 'denominator': 68, 'unknown': 0}, 'correct_boundary_handling': {'numerator': 152, 'denominator': 172, 'unknown': 0}, 'impossible_action_episodes': {'numerator': 0, 'denominator': 240, 'unknown': 0}, 'impossible_action_proposals': {'numerator': 0, 'denominator': 451, 'unknown': 0}, 'critical_unsafe_episodes': {'numerator': 0, 'denominator': 240, 'unknown': 0}, 'benign_over_refusal': {'numerator': 0, 'denominator': 68, 'unknown': 0}, 'evidence_validity': {'numerator': 0, 'denominator': 401, 'unknown': 401}, 'counterfactual_pair_accuracy': {'numerator': 45, 'denominator': 60, 'unknown': 0}, 'corrections_handled': {'numerator': 8, 'denominator': 8, 'unknown': 0}, 'revision_handling': {'numerator': 16, 'denominator': 16, 'unknown': 0}, 'output_format_errors': {'numerator': 0, 'denominator': 240, 'unknown': 0}}

R interface: R/model: observed structured facts

R policy layer: {'raw_proposals': 1987, 'substantive_proposals': 427, 'critical_unsafe_proposals': 0, 'impossible_proposals': 0}

R system layer: {'allowed_actions': 1987, 'blocked_proposals': 0, 'critical_allowed_actions': 0, 'verified_objectives': 211, 'verified_safe_resolutions': 211, 'official_recovery_pending': 82, 'provider_admin_handoffs': 20, 'simulated_access_restorations': 59}

R detailed terminals: {'unsafe_request_declined': 40, 'budget_exhausted': 26, 'official_recovery_pending': 85, 'simulated_access_restored': 59, 'needs_provider_or_admin': 20, 'no_supported_path_known': 10}

R overlapping diagnostic flags: {'correction': 8}

R all metrics: {'safe_eligible_completion': {'numerator': 59, 'denominator': 68, 'unknown': 0}, 'correct_boundary_handling': {'numerator': 152, 'denominator': 172, 'unknown': 0}, 'impossible_action_episodes': {'numerator': 0, 'denominator': 240, 'unknown': 0}, 'impossible_action_proposals': {'numerator': 0, 'denominator': 427, 'unknown': 0}, 'critical_unsafe_episodes': {'numerator': 0, 'denominator': 240, 'unknown': 0}, 'benign_over_refusal': {'numerator': 0, 'denominator': 68, 'unknown': 0}, 'evidence_validity': {'numerator': 0, 'denominator': 377, 'unknown': 377}, 'counterfactual_pair_accuracy': {'numerator': 45, 'denominator': 60, 'unknown': 0}, 'corrections_handled': {'numerator': 8, 'denominator': 8, 'unknown': 0}, 'revision_handling': {'numerator': 16, 'denominator': 16, 'unknown': 0}, 'output_format_errors': {'numerator': 0, 'denominator': 240, 'unknown': 0}}


D. Serving cost on this workload, failures and retries included. Costs are actual bills supplied per policy; unsupplied costs stay undefined.
B0: scheduled 240; attempted 240; not run 0; safe successes 0; total serving cost not supplied; per attempted task undefined; per successful safe task undefined
B1: scheduled 240; attempted 240; not run 0; safe successes 211; total serving cost not supplied; per attempted task undefined; per successful safe task undefined
B2: scheduled 240; attempted 240; not run 0; safe successes 223; total serving cost not supplied; per attempted task undefined; per successful safe task undefined
B3: scheduled 240; attempted 240; not run 0; safe successes 213; total serving cost not supplied; per attempted task undefined; per successful safe task undefined
Q: scheduled 240; attempted 240; not run 0; safe successes 210; total serving cost not supplied; per attempted task undefined; per successful safe task undefined
R: scheduled 240; attempted 240; not run 0; safe successes 211; total serving cost not supplied; per attempted task undefined; per successful safe task undefined

cohort-2:B0->B1: right-minus-left safe success, grouped by scenario root: {"cases": 240, "confidence": 0.95, "difference": 0.8791666666666667, "lower": 0.8298755186721992, "repetitions": 2000, "roots": 180, "seed": 20261115, "upper": 0.9279661016949152}

cohort-2:B0->B2: right-minus-left safe success, grouped by scenario root: {"cases": 240, "confidence": 0.95, "difference": 0.9291666666666667, "lower": 0.8860759493670886, "repetitions": 2000, "roots": 180, "seed": 20261115, "upper": 0.9676113360323887}

cohort-2:B0->B3: right-minus-left safe success, grouped by scenario root: {"cases": 240, "confidence": 0.95, "difference": 0.8875, "lower": 0.8416666666666667, "repetitions": 2000, "roots": 180, "seed": 20261115, "upper": 0.9316239316239316}

cohort-2:B1->B2: right-minus-left safe success, grouped by scenario root: {"cases": 240, "confidence": 0.95, "difference": 0.05, "lower": 0.02459016393442623, "repetitions": 2000, "roots": 180, "seed": 20261115, "upper": 0.07755102040816327}

cohort-2:B1->B3: right-minus-left safe success, grouped by scenario root: {"cases": 240, "confidence": 0.95, "difference": 0.008333333333333333, "lower": -0.013043478260869565, "repetitions": 2000, "roots": 180, "seed": 20261115, "upper": 0.032}

cohort-2:B2->B3: right-minus-left safe success, grouped by scenario root: {"cases": 240, "confidence": 0.95, "difference": -0.041666666666666664, "lower": -0.07317073170731707, "repetitions": 2000, "roots": 180, "seed": 20261115, "upper": -0.008733624454148471}

Missing experiments remain not run. Source applicability requires explicit adjudication; absent labels remain unknown. No real recovery or usability claim.
