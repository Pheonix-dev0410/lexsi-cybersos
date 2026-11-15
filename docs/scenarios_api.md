# Scenario generation and splits API

Public APIs:

- `cybersos.data.split_assignment.build_scenario_splits` — builds seeded splits from a diagnostic JSONL path.
- `cybersos.data.split_artifacts.save_scenario_splits` — saves validated JSONL, root hashes, and manifest.
- `cybersos.data.split_leakage_gates.validate_scenario_splits` — checks leakage, pair integrity, allocations, and independent-root counts.
- `cybersos.data.scenario_wording.render_episodes` — generates paraphrases after root assignment.
- `cybersos.data.scenario_loading.load_scenario_splits` / `load_training_episodes` — read saved splits; the latter validates every split before returning the training episodes.
- `cybersos.data.diagnostic_scenarios.load_diagnostic_scenarios` — loads authored diagnostics or saved split rows into `DiagnosticCase` records, parsing roots exactly like `scenario_loading`.

Full profile 400 train / 60 dev / 240 test; reduced 240 / 40 / 120; 30 independently constructed test roots.

## Hidden state and opening disclosures

Every template starts from `base_access_state(owner=...)`: one explicit default per access
field (the template's ownership, a personal adult account, a known password, a safe other
device, no extra factor). Templates then apply their changes, and a counterfactual pair
flips exactly one field with `counterfactual_value`.

The opening message states only a few facts, and `initial_facts` holds exactly those:
ownership ("my account"), an unavailable phone for lost-phone incidents, the facts the
template's opening sentence states, and at most one incident-relevant detail chosen from
the hidden state. Everything else, including the pair's deciding field, stays unknown until
the policy asks. A template's `misreported` facts are stated wrongly and later corrected by
a simulator `UserCorrection`; every other initial fact equals the hidden value.

Because openings are short, different hidden states can share wording; rendering redraws a
paraphrase until no opening message is shared across splits.

`DiagnosticCase` preserves authored family, split, expected permissible actions, terminal
boundary, and root metadata. Use `case.scenario` for simulation and `case.episode` for
the development split. Reviewed collections retain the 36-case/six-family validation;
plain scenario collections do not require diagnostic authoring metadata.

`Scenario.corrections`, `temporary_tool_failures`, and `access_answers` are serialized
and included in state/root hashes. Corrections use `after_question` or `after_step_id`
semantic triggers. Temporary failures name a tool and optionally a step, fail once,
and allow retry. See `core_api.md` for field contracts.
