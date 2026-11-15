# Evaluation API

| Names | Purpose |
|---|---|
| `schedule_cases`, `schedule_scenario`, `run_batch`, `ScheduledCase` | Schedule cases and run every episode through one loop. |
| `RunIdentity`, `CaseInfo`, `TraceRecord`, `record_episode` | Capture scheduled cases and trusted evidence. |
| `write_traces`, `load_traces` | Persist complete core traces as JSONL. |
| `summarize`, `summarize_slices` | Denominators, revision handling, over-refusal, diagnostics and efficiency. |
| `evaluate_recorded`, `SCORER_VERSION` | AuditKIT state assertions and versioned predicate, offline. |
| `paired_bootstrap`, `compare_checkpoints` | Seeded differences grouped by scenario root. |
| `render_results_tables`, `write_preflight_report` | Tables A/B/C and the diagnostic report. |
| `RunManifest`, `output_cache_key` | Reproducibility record and the single cache-key function. |
| `serving_cost`, `evaluation_seconds` | Cost worksheet and final-evaluation time reservation. |

Library names import from `cybersos.evaluation`. Details: `src/cybersos/evaluation/README.md`.
Protocol: `configs/eval.yaml`; it must agree with the serving contract `configs/baselines.yaml`.

## Commands

Run from any directory with `.venv/bin/python`; defaults resolve from the project root. Each
command supports `--help` and exits nonzero on invalid configuration, incomplete execution or
missing artifacts. Model stages need the shared GPU environment.

| Milestone | Command | Output |
| --- | --- | --- |
| D0 / M0 | `scripts/doctor.py --stage inference` / `--stage data` | `reports/doctor-<stage>.json` |
| D1 | `scripts/diagnose_baseline.py` (add `--include-base --base-manifest configs/base_model.json` for B0) | `reports/preflight.md`, `reports/diagnostic/{Q,R,B0}/` |
| M6b | `scripts/evaluate.py --split dev --checkpoint runs/sft-adapter --base-manifest configs/base_model.json` | `reports/runs/dev/B1-<key>/` |
| M6c | `scripts/report.py --runs reports/runs/dev --stage sft-residuals --remaining-seconds N` | `reports/sft_residuals.md` |
| M9 | `scripts/evaluate.py --split test --checkpoint base --base-manifest configs/base_model.json` | `reports/runs/test/B0-<key>/` |
| M9 | `scripts/evaluate.py --split test --checkpoint runs/sft-adapter --base-manifest configs/base_model.json` | `reports/runs/test/B1-<key>/` |
| M10 | `scripts/report.py --runs reports/runs [--serving-cost B1=AMOUNT]` | `reports/results.md`, `reports/results.json` |
| M11 | `scripts/package_submission.py --check` | `reports/submission_inventory.{md,json}` |

- `--checkpoint` takes `base`, `Q`, `R` or a local PEFT adapter directory; use `--policy-label B2`
  for an AgentTune adapter. Download remote adapters to a pinned local directory first.
- A run directory is never overwritten; use another `--output` for a declared rerun and select the
  intended sweep when reporting. Several sweeps of one policy in one cohort are rejected.
- A model setup failure keeps every case as `not_run` and exits 1. Timeouts, generation failures,
  environment failures and aborted episodes keep distinct statuses. Generated-answer caching is off.
- Weight comparisons require matching manifests (data, split, prompt, tools, guard, runtime,
  orchestration and environment).
- `doctor --stage align|agent --adapter PATH` also reloads a saved adapter in a fresh process. When
  the environment has no `pip` (uv venvs), the dependency check uses `importlib.metadata` and
  reports the method used.
- File existence in the submission inventory does not prove public access or a passed review.
