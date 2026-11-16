# CyberSOS

**A recovery-planning agent that chooses its next step from the access a person still has.**

> Can post-training teach a small Cohere model to choose and revise feasible recovery actions from incomplete, changing access information — while reducing unsupported steps without refusing legitimate help?

CyberSOS covers personal Google accounts and Android devices in three situations: a lost phone or second factor, an exposed password, and a lockout. A policy asks one question or proposes one step per turn. Deterministic code checks every proposal against reviewed rules from official Google help pages. Training and evaluation run in a simulator, and the app never signs in, resets, erases or transfers anything.

## Status

| Stage | State |
| --- | --- |
| Rules, simulator, guard, episode loop, Q and R baselines, oracle | Built and tested |
| Scenarios: 400 train, 60 dev and 240 locked test episodes (30 independently constructed test roots) | Generated with seed `20261113` |
| Training rows from verified trajectories (teacher: observed-state planner R on 371 of 400 episodes, oracle route on 29): 3,062 candidates, 2,958 accepted by CuratorKIT (104 exact duplicates) | Generated |
| Q and R on diagnostic, dev and test | Run on CPU |
| B0 (untuned Tiny Aya) and B1 (SFT, LoRA r=16, one epoch) on dev and the locked test split | Run on Modal (`deploy/modal/`) |
| B2 (AgentTune GRPO from B1) | **Best policy.** 20 steps on one H200, 8 rollouts per scenario at temperature 1.0, on the training scenarios B1 failed in 1,200 student rollouts (`scripts/rollout_student.py`). A first run at temperature 0.7 on random scenarios had zero reward variance in every group (B1 entropy ≈ 0.001) |
| B3 (DAgger: R relabels every state B1 reached, 830 new gated rows, SFT from base) | Ablation: fewest unsafe proposals, no gain in objectives |
| Gradio app with four views and three demo cases | Builds and serves locally; uses R until a checkpoint is supplied |

Test suite: **357 tests**, offline, CPU only, about 15 seconds.

## Measured results

All rows share one frozen serving contract (`configs/baselines.yaml`): same prompt, tools, guard, 12-action and 1,792-token budgets, greedy decoding. Only the policy changes. Scripted question counts are burden proxies, not user effort.

**Locked test split (240 episodes, 180 independent resampling units)**

| Policy | Safe eligible completion | Correct boundary handling | Episodes with a critical unsafe *proposal* (all blocked) | Questions asked |
| --- | --- | --- | --- | --- |
| Q: guided questionnaire | 58/68 | 152/172 | 0/240 | 1,588 |
| R: observed-state planner | 59/68 | 152/172 | 0/240 | — |
| B0: Tiny Aya, untuned | 0/68 | 0/172 | 0/240 | — |
| B1: Tiny Aya + SFT | 53/68 | 158/172 | 22/240 | 1,502 |
| **B2: Tiny Aya + SFT + GRPO** | **58/68** | **165/172** | 13/240 | — |
| B3: Tiny Aya + SFT on DAgger data | 53/68 | 160/172 | **7/240** | — |

Objectives met: B0 0, Q 210, R 211, B1 211, **B2 223**, B3 213 of 240. Paired bootstrap over scenario roots (counterfactual pairs resampled together), 95% intervals: B0 → B1 **+87.9 points** [83.0, 92.8]; **B1 → B2 +5.0 points [2.5, 7.8]**; B0 → B2 +92.9 [88.6, 96.8]; B1 → B3 +0.8 [−1.3, 3.2]; B3 → B2 +4.2 [0.9, 7.3]. Dev (60 episodes): B0 0, B1 41, B2 42, B3 32, Q and R 57; B1 → B2 on dev is +1.7 [−7.0, +9.7], so dev alone does not resolve it.

What this shows, plainly:

- **SFT teaches the action contract.** Untuned Tiny Aya chooses plausible actions but wraps every one in a Markdown code fence, so the strict one-action parser rejects all of them (240/240 output-format failures). After SFT, 5/240 episodes have a format error.
- **B1 is a distillation of R, not an improvement on it.** It matches R on overall objectives (211 vs 211 of 240), handles more boundary cases (158 vs 152), but completes fewer eligible restorations (53 vs 59).
- **B2 improves on its teacher.** GRPO, rewarded only by trusted environment events, lifts objectives to 223/240, eligible completion to 58/68 and boundary handling to 165/172, and cuts episodes with a critical unsafe proposal from 22 to 13 (all blocked by the guard in both).
- **GRPO needs within-group disagreement.** On a near-deterministic SFT policy, random scenarios give every group identical rewards. Sampling at temperature 1.0 and drawing scenarios only from those the SFT student failed made every group informative.
- **DAgger trades success for caution.** Relabeling every state B1 reached with R (B3) gives the fewest critical unsafe proposals on test (7/240) but no gain in objectives (+0.8, interval spans 0), and on dev it over-asks (339 → 512 questions; 27/60 budget exhaustions) and scores 32/60, below B1 (−15.0 [−28.8, −3.1]).

How we got here (dev, kept in `runs/superseded-evaluations/`): the first B1 learned from the oracle route, which picks questions from hidden state; it collapsed to the most common route (18/60). Switching the teacher to R, which decides only from observed facts, gave 41/60. Listing the closed set of step ids in the tool signatures removed near-miss invented ids (22 → 0) but left the headline unchanged (40/60).

Full tables: `reports/results.md`, `reports/preflight.md`.

## Setup

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e '.[dev,app]' -e vendor/CuratorKIT -e vendor/AuditKIT
.venv/bin/python -m pytest -q
```

`vendor/` holds the Lexsi repositories at these commits: CuratorKIT `ed45ae3`, aligntune `b6e924e`, AgentTune `1dfd054`, AuditKIT `556eb48`. Clone them with `git clone https://github.com/Lexsi-Labs/<repo>.git vendor/<repo>` followed by `git -C vendor/<repo> checkout <sha>`.

## Commands

Data and baselines (CPU):

```bash
.venv/bin/python scripts/doctor.py --stage data
.venv/bin/python scripts/build_scenarios.py --seed 20261113      # frozen train/dev/test splits
.venv/bin/python scripts/build_decisions.py --seed 20261113      # verified teacher trajectories -> decision rows
.venv/bin/python scripts/curate.py --seed 20261113               # CuratorKIT exact dedup + data gates
.venv/bin/python scripts/diagnose_baseline.py                    # Q/R (and B0 with --include-base) -> reports/preflight.md
.venv/bin/python scripts/evaluate.py --split dev --checkpoint R  # any of Q, R, base, or an adapter path
.venv/bin/python scripts/report.py --runs reports/runs           # reports/results.md
.venv/bin/python app.py                                          # local demo
```

Model stages (Linux, CUDA, Tiny Aya access accepted):

```bash
.venv/bin/python scripts/doctor.py --stage inference
.venv/bin/python scripts/diagnose_baseline.py --include-base --base-manifest configs/base_model.json
.venv/bin/python scripts/render_decisions.py --tokenizer artifacts/base   # one rendered training file
.venv/bin/python scripts/train_sft.py --config configs/sft.yaml --smoke
.venv/bin/python scripts/train_sft.py --config configs/sft.yaml
.venv/bin/python scripts/evaluate.py --split dev --checkpoint runs/sft-adapter
.venv/bin/python scripts/report.py --runs reports/runs --stage sft-residuals
.venv/bin/python scripts/rollout_student.py --checkpoint runs/sft-adapter-v3 --temperature 1.0 --samples 2 --output reports/dagger/student.jsonl
.venv/bin/python scripts/train_agent.py --config configs/agent.yaml           # GRPO on the scenarios the student failed (B2)
.venv/bin/python scripts/relabel_on_policy.py reports/dagger/*.jsonl          # DAgger rows: R labels every state the student reached (B3)
```

On Modal, `deploy/modal/run_job.sh <job>` runs each of these stages detached (H200 for training and evaluation, L40S shards for student rollouts; see `deploy/modal/README.md`). The base model is pinned to revision `af89d219…` of `CohereLabs/tiny-aya-global` with Transformers 5.23.0 and Torch 2.11.0; after any change to rules or guard sources run `scripts/freeze_serving_contract.py`. Every checkpoint is evaluated under that one frozen serving contract: same prompt, tools, guard, budgets and decoding. Only the weights change.

## How it fits together

```
opening message ──► policy (Q | R | Tiny Aya) ──► raw proposal logged
                                                     │
                                       parse ──► guard ──► simulator tools ──► observation
                                                     │                             │
                                                     └──────── trace ◄──────────────┘
                                                                 │
                                          metrics · AuditKIT · reports · app evidence view
```

| Package | Responsibility |
| --- | --- |
| `domain` | Access fields, scenarios, observed facts with provenance, actions, outcomes |
| `playbooks` | Source registry, the 16 reviewed rules, the one prerequisite evaluator |
| `simulator` | Episode state, scripted answers and provider responses, corrections, tool failures |
| `safety` | Strict one-action parsing; the guard (secrets, URLs, prerequisites, destructive steps) |
| `runtime` | Policy protocol and the episode loop that produces traces |
| `baselines` / `oracle` | Q questionnaire and R planner; evaluator-only reachability and reference routes |
| `policy` | Observation rendering, prompt templates, chat serialization, frozen serving contract |
| `data` | Scenario generation, root-level splits, decision rows, curation, data gates |
| `training` | AlignTune SFT wrapper, trajectory reward, AgentTune rollout bridge and patch |
| `evaluation` | Batch runner, metrics, bootstrap, AuditKIT bridge, reports, run manifests |
| `app` | Gradio views: incident guidance, practice drill, evidence, about |
| `serialization` | Hashing, JSON/JSONL files, strict YAML — shared by every package |

API notes for each area are in `docs/`.

## Boundaries

- The policy sees only the opening message, its own actions, and their observed results. It never sees hidden state, gold actions or provider scripts.
- Every URL comes from the source registry; a URL the model writes is blocked and stripped before it is echoed back.
- No password, code, backup-code value, session token or identity document is ever requested or stored.
- Unsafe proposals count against the policy even when the guard blocks them. Outcomes come from simulator events, never from the model's words.
- "Simulated access restored", "official recovery pending" and a person's own report of success are kept separate. Benchmark success is not evidence of real recovery.

## License and attribution

The base model, `CohereLabs/tiny-aya-global`, is gated and licensed for noncommercial use. Published adapters must carry its attribution and terms. The rules summarize official Google help pages (`data/sources.yaml`), with links and review dates.
