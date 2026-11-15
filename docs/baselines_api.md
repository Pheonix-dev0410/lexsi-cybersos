# Baselines and oracle API

| Import | Purpose |
|---|---|
| `cybersos.baselines.GuidedQuestionnaire` | Q: fixed, per-incident branching wizard implementing `Policy`; reviewed typed flows live in `baselines/questionnaire_flows.py`. Uses yes / no / don't know availability controls, honors initial disclosures, completes each required page in order, and recommends a supported route at its declared endpoint. Recomputes branches after corrections; never ranks questions by information value. |
| `cybersos.baselines.ObservedStatePlanner` | R: adaptive observed-state planner implementing `Policy`; executes ready routes or prioritizes routes needing fewer unknown prerequisites. Uses core prerequisite evaluation and shares route ordering and sourced finish construction (`cybersos.playbooks.finish_action`) with Q, but has its own decision procedure. |
| `cybersos.oracle.reachable_routes` | Full-state reachability returning `Reachability` and `ReferenceRoute` records. |
| `cybersos.oracle.reference_trajectory` | Generates a verified training witness with observed-action traces. |
| `cybersos.oracle.verified_terminal_objective` | Verifies completion against trusted events. |
| `cybersos.oracle.safe_resolution` | Also rejects critical raw proposals, including blocked ones. |
| `cybersos.data.diagnostic_scenarios.load_diagnostic_scenarios` | Sole diagnostic loader, returning `DiagnosticCase` records. |

Diagnostic cases: `data/scenarios/diagnostic.jsonl` (36 cases, metadata envelope around `Scenario`; load with `load_diagnostic_scenarios`). Run a case with `run_episode(policy, RecoveryEnvironment(case.scenario, registry, episode_id=...))`.

Baselines and the oracle derive step progress from what a policy can observe
(`cybersos.simulator.observed_progress`) and from trusted events, both through
`cybersos.simulator.step_evidence`, so they credit exactly the evidence the simulator does.
The oracle never imports `cybersos.baselines`.

`DiagnosticCase` is owned by `cybersos.data.diagnostic_scenarios`. Scripted corrections live on
`case.scenario.corrections` and run inside the simulator. `case.episode` supplies the
development-split `ScenarioEpisode` used by split assignment.
