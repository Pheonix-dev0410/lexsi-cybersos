# Core API (domain, playbooks, simulator, safety, runtime)

Import from the package level shown. Read the source for signatures.

| Import path | Names and purpose |
|---|---|
| `cybersos.domain.access` | `AccessField`, `Availability`, `BackupCodeStorage` — approved availability fields and values. |
| `cybersos.domain.scenario` | `Scenario`, `Permissions`, `Provider`, `Incident` — immutable scenario configuration. |
| `cybersos.domain.observed_facts` | `ObservedFacts`, `Fact`, `FactSource` — provenance, revisions, conflicts, and corrections. |
| `cybersos.domain.actions` | `Action`, `ToolName` — canonical action serialization. |
| `cybersos.domain.outcomes` | `TerminalState`, `ExecutionStatus`, `TaskOutcome`, `SessionMode`, `ProviderResponse` — distinct outcome categories. |
| `cybersos.playbooks` | `load_playbooks`, `PlaybookRegistry`, `RecoveryRule`, `Source` — validated rules and destinations. |
| `cybersos.playbooks` | `evaluate_prerequisites`, `PrerequisiteResult`, `Readiness` — centralized prerequisite evaluation. |
| `cybersos.playbooks` | `load_project_registry`, `RULES_REVIEWED_ON` — the shipped rule set; `finish_action` — a finish citing its step's registry sources. |
| `cybersos.simulator` | `RecoveryEnvironment`, `EpisodeTools` — isolated episodes and five bound tools. |
| `cybersos.simulator` | `Observation`, `ActionObservation`, `ToolResult`, `Event`, `TrustedSnapshot`, `render_tool_result` — observations, evidence, and result serialization. |
| `cybersos.simulator` | `step_evidence`, `StepEvidence` — the one mapping from a step's observed response to completion and terminal evidence; `supported_conclusions` — terminal states the evidence supports. |
| `cybersos.simulator` | `observed_progress`, `ObservedProgress` — attempts, completions and evidence derivable from an observation's own history. |
| `cybersos.safety` | `parse_action`, `ParsedProposal`, `guard_action`, `GuardContext`, `GuardVerdict`, `Violation`, `ViolationKind`, `content_violations` — strict parsing and typed safety decisions. |
| `cybersos.safety` | `assistance_declined(facts, opening_message)` — the one ownership / unauthorized-request check shared by the guard and conclusion support. |
| `cybersos.runtime` | `Policy`, `EpisodeRunner`, `run_episode`, `DecisionTrace`, `EpisodeTrace`, `PolicyTimeoutError`, `PolicyBudgetExceeded` — callable policies, resumable incident sessions, and complete traces. |

- A policy is any callable `(Observation) -> str` returning raw model-style text; `run_episode` / `EpisodeRunner` drive it through parse -> guard -> environment and return an `EpisodeTrace`.
- Rule predicates are evaluated only by `cybersos.playbooks.evaluate_prerequisites`.
- A `RecoveryEnvironment` keeps its mutable episode state in one `EpisodeState`
  (`simulator/episode_state.py`) that it passes to the transition helpers; nothing reaches into
  the environment's private attributes.
- `Action.as_internal()` and `render_tool_result` convert values with `cybersos.serialization.to_json_value`.
- Rules: `data/playbooks.yaml` (16 rules), sources: `data/sources.yaml`.

`Observation.action_history` contains `ActionObservation(action, guard_verdict, result)`
records for accepted and blocked proposals. Unparseable proposals have `action=None`
and retain `raw_proposal` for policy feedback; raw text is also in the trusted event log. `Observation.history` remains the result-only
view. Incident reports update the pending action's result. Neither view exposes scenario
scripts, future corrections, failures, hidden access, or evaluator metadata.

`Scenario` adds these benchmark-only scripts (also accepted as mappings by
`Scenario.from_mapping`):

- `corrections: tuple[UserCorrection, ...]`: `field`, `value`, exactly one of
  `after_question` (access field) or `after_step_id` (attempted step), optional `message`.
  Each fires once after its semantic event; the corrected answer replaces the active
  fact and future scripted answer while preserving fact history. Prerequisites are
  evaluated afresh against the new revision before dispatch.
- `temporary_tool_failures: tuple[TemporaryToolFailure, ...]`: `tool_name` and optional
  `step_id`. Each fails once with `error='temporary_tool_failure'`, `retryable=True`;
  it consumes an action but no provider response or attempted step. A retry is allowed.
- `access_answers`: approved field/value overrides for the scripted responder, including
  `'unknown'` when a person does not know. An explicitly answered unknown prerequisite
  can support `no_supported_path_known` when every route is blocked, attempted, or
  depends on such an answer. Unasked or conflicted facts alone cannot justify this stop.

`UserCorrection` and `TemporaryToolFailure` are exported from `cybersos.domain`;
`ActionObservation` from `cybersos.simulator`. Incident guidance uses actual user reports
and does not execute benchmark scripts.

Policies may raise `cybersos.runtime.PolicyTimeoutError` for `execution_status='timeout'`
or `PolicyBudgetExceeded` for terminal state `budget_exhausted`. Both token and action
budget exhaustion record execution status `finished` and outcome `objective_not_met`
in benchmark mode. Other policy exceptions remain `generation_error`.
