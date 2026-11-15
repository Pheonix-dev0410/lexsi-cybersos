# CyberSOS: teaching Tiny Aya to plan account recovery from the access a person still has

**One-line claim:** SFT on 2,958 planner-verified decisions takes `tiny-aya-global` from 0/240 to 210/240 safely resolved recovery episodes on a locked test set (+87.5 points, 95% CI [82.4, 92.4]), matching the rule planner it was distilled from.

**Tracks and problem statements covered**
- Track 1: Fine-tuning and Data Curation (CuratorKIT → AlignTune → AuditKIT)
  - Problem statement 3: Grounded answers and fewer hallucinations. Every action must come from 16 reviewed rules drawn from official help pages. The model says so when no supported path exists, and unsupported proposals are counted.
  - Problem statement 5: Structured output and extraction. Each turn is exactly one schema-validated JSON action; output-format failures fell from 240/240 to 5/240.
- AgentTune (Track 3 tooling) was integrated and run, but produced no usable adapter (see Results). We do not claim Track 3.

**Content warning:** none. All scenarios are synthetic; no real accounts, credentials or personal data.

## Abstract

People who lose a phone, leak a password or get locked out of a Google account need the *next feasible step* given what they still have. Generic chatbots recite help articles, ask for secrets, or suggest steps the person cannot take. CyberSOS is a recovery-planning agent: each turn it asks one access question or proposes one step, a deterministic guard checks every proposal against 16 reviewed rules drawn from official Google help pages, and a simulator decides outcomes. It never signs in, resets, erases or transfers anything.

**Headline (locked test, 240 episodes):** untuned Tiny Aya 0/240 → SFT 210/240 objectives met (+87.5 pts safe success, 95% paired-bootstrap CI [82.4, 92.4]). The rule planner it learned from scores 211/240.

**Base model and method:** `CohereLabs/tiny-aya-global` (rev `af89d219`, bf16) + LoRA SFT (r=16, 1 epoch) via AlignTune on 2,958 CuratorKIT-deduplicated decisions from an observed-state planner, scored with AuditKIT under one frozen serving contract.

> **For judges, one minute:** the untuned model picks sensible actions but wraps every one in a Markdown code fence, so a strict one-action parser rejects all 240 episodes. SFT fixes the action contract and decision sequencing. B1 handles more boundary cases than the rule planner (157 vs 152 of 172) but completes fewer eligible restorations (53 vs 59 of 68). The guard blocked every unsafe proposal: 0 critical actions executed, though B1 *proposed* one in 23/240 episodes. AgentTune GRPO ran on an H200 but found zero reward variance: the SFT model's eight rollouts per prompt were identical, so there was nothing to learn.

## Problem statement and approach

**Why this problem.** Account-recovery help fails in a predictable way: it gives a fixed checklist, asks for codes or passwords, or recommends a step the person cannot take ("use your backup phone" after the phone was stolen). A useful assistant must reason about which access factors the person *actually* has, ask when a fact is unknown, and hand off honestly when no supported path exists.

**Research question.** Can post-training teach a small Cohere model to choose and revise feasible recovery actions from incomplete, changing access information while reducing unsupported steps without refusing legitimate help?

**Hypotheses.** (H1) The untuned model fails on the action contract, not on intent. (H2) SFT on observed-state planner trajectories closes most of the gap to the planner. (H3) GRPO adds value only if SFT rollouts vary in outcome.

**Threat model / boundaries.** The policy sees only the opening message, its own actions and their observed results, never hidden state or gold labels. URLs come only from a source registry; model-written URLs are stripped. No password, code, backup-code value, session token or ID document is ever requested. Unsafe proposals count against the policy even when blocked.

## Hackathon repos (kits) used

| Kit (pinned commit) | How it was used |
| --- | --- |
| **CuratorKIT** `ed45ae3` | SchemaGate + ExactDeduplicator + AlpacaExporter over 3,062 candidate decisions → 2,958 accepted (104 exact duplicates removed). Counterfactual pairs that differ in one access flag are checked to survive. |
| **AlignTune** `b6e924e` | `create_sft_trainer` (TRL backend, instruction-following, alpaca format, completion-only loss, LoRA). We verify the trainer's real label masks match the inference token sequence exactly, then reload the adapter in a fresh process. |
| **AgentTune** `1dfd054` | Agentic GRPO with a recorded rollout patch (one validated action per turn, stop on `finish`, frozen generation budget) and trajectory rewards from simulator events. Ran 5 steps; see Results. |
| **AuditKIT** `556eb48` | Independent scoring of recorded episodes from trusted simulator outcomes, plus tool-call diagnostics. |

**How they connect:** scenarios → planner trajectories → per-decision rows → **CuratorKIT** → rendered with Tiny Aya's own chat template → **AlignTune** SFT → (**AgentTune** GRPO) → evaluation runner (same prompt, guard, budgets, greedy decoding for every checkpoint) → traces → **AuditKIT** + our metrics + paired bootstrap.

## Models and licenses

- **Base:** `CohereLabs/tiny-aya-global`, revision `af89d219b53ed9b13b8a4645f9c8028973510324`, bf16, no quantization, Transformers 5.23.0, Torch 2.11.0. License CC-BY-NC-4.0 (gated; terms accepted).
- **Teacher:** no LLM teacher. A deterministic observed-state planner (R) produced 371 of 400 training trajectories; an evaluator-only oracle route covered the 29 that R could not finish within budget. Rationale: the policy must imitate decisions it can justify from what it sees. Our first SFT used the oracle as primary teacher; it chose questions from hidden state and the model collapsed to the most common route (18/60 dev vs 41/60 with R).

## Datasets, benchmarks and licenses

- **Source:** fully synthetic, generated by our scenario generator (seed `20261113`) over 16 rules summarizing official Google help pages (`data/sources.yaml`, with links and review dates).
- **Languages:** English only.
- **Splits:** 400 train / 60 dev / 240 locked test episodes, plus 36 diagnostic cases. Splits are assigned by scenario root, so paraphrases of one problem never cross splits. Leak checks: exact root-hash and fingerprint matching across splits, and counterfactual pairs are verified complete and not collapsed by dedup. The test set includes 30 independently constructed roots.
- **CuratorKIT filtering:** 3,062 → 2,958 (104 exact duplicates). Our own gates also reject secrets/PII, infeasible actions, unsupported sources and replay mismatches; 0 rows were rejected by them in the final build.
- **Tool environment and trajectories:** deterministic recovery simulator with five tools (`ask_access`, `lookup_playbook`, `check_step`, `simulate_step`, `finish`), scripted provider responses, user corrections and temporary tool failures.

## Metrics, and why these

| Metric | Direction | Why |
| --- | --- | --- |
| Safe eligible completion | higher | Restores access when a supported path exists, with no unsafe proposal |
| Correct boundary handling | higher | Correct handoff (official recovery, admin, honest limitation, decline unauthorized) |
| Critical unsafe episodes (proposed) | lower | Counted even when the guard blocks them |
| Benign over-refusal | lower | Refusing legitimate help is a failure |
| Output-format errors | lower | Strict one-action contract |
| Questions asked | lower | Interaction-burden proxy |

**What should not get worse:** over-refusal stayed at 0/68 for every policy, and no critical action was ever executed. **Judge check:** outcomes come from simulator events, never model text; AuditKIT scores the recorded traces independently.

## Method / experiments

- **Serving contract** (`configs/baselines.yaml`, hash-pinned): one system prompt, plain-text tool signatures, compact observation rendering (facts, retrieved rules, call history), 12-action budget, 1,792 prompt and 128 generation tokens, greedy decoding, stop at `<|END_RESPONSE|>`. Only weights change between checkpoints.
- **AlignTune SFT:** 1 epoch, batch 1 × grad-accum 8 (370 steps), lr 1e-4, LoRA r=16 / α=32 / dropout 0.05 on all linear layers, gradient checkpointing, bf16, completion-only loss, seed 42. 24 minutes on one L40S.
- **AgentTune GRPO:** from the SFT adapter, 64 pilot scenarios, 8 generations per prompt, batch 8, lr 1e-5, max 10 steps, bf16, one H200.
- **Seeds:** data 20261113, training 42, bootstrap 20261115.
- **Ablations (dev, 60 episodes):** oracle teacher 18/60 → observed-state teacher 41/60 → plus closed step-id vocabulary in tool signatures 40/60 (invented step ids 22 → 0; headline unchanged).

## Results

**Same model before vs after (locked test, 240 episodes)**

| Policy | Safe eligible completion | Correct boundary handling | Critical unsafe proposals (all blocked) | Format errors | Questions |
| --- | --- | --- | --- | --- | --- |
| Q: guided questionnaire | 58/68 | 152/172 | 0/240 | 0 | 1,588 |
| R: observed-state planner | 59/68 | 152/172 | 0/240 | 0 | — |
| **B0: Tiny Aya (untuned)** | 0/68 | 0/172 | 0/240 | 240/240 | — |
| **B1: Tiny Aya + SFT** | **53/68** | **157/172** | 23/240 | 5/240 | 1,502 |

B0 → B1: **+87.5 pts** safe success, 95% CI [82.4, 92.4], paired bootstrap over 180 scenario clusters (counterfactual pairs resampled together). Dev agrees: B0 0/60, B1 40/60, Q/R 57/60.

**Findings**
1. **The base model's failure is the contract, not intent.** It proposes sensible actions inside code fences and repeats them after each block.
2. **Teacher choice dominates.** An oracle teacher leaks hidden-state choices that the policy cannot imitate.
3. **SFT distils the planner, it does not beat it.** B1 handles more boundary cases than R, completes fewer eligible restorations, and its residual errors are timing errors: acting before prerequisites are known, or finishing without server evidence.

**What didn't work**
- **AgentTune GRPO.** Across 5 steps, every group of 8 rollouts was identical (B1 entropy ≈ 0.001), so the reward standard deviation and the gradients were effectively zero; step 6 ran out of memory. No B2 adapter was evaluated.
- **Listing step ids in the tool signatures.** It removed invented ids but did not raise the headline.

**Sample (B1, test).** *"I enrolled a physical security key, but I need to check if I can reach it."* → `ask_access` organization_managed=false → child_account=false → safe_other_device=true → independent_passkey_available=false → password_known=true → enrolled_security_key_available=true → `simulate_step use_security_key` → `finish simulated_access_restored [google_2sv]` (verified by the simulator).

## Cost / ROI

- **Compute:** Modal, about 3 L40S-hours (snapshot, smoke and full SFT ×3, dev/test evals) plus about 1 H200-hour (AgentTune). Total bill: **$15**.
- **Serving:** B1 averages 8.2 s per episode (about 8 model calls) on one L40S with HF `generate`, not vLLM. That is ≈ 2.3 GPU-hours per 1k episodes, about $4.50 per 1k episodes or ≈ $0.56 per 1k replies. No closed-model API baseline was run.

## Limitations

- English only; personal Google accounts and Android devices only; 16 rules.
- Results are in a deterministic simulator: simulated restoration is not real recovery, and provider decisions are scripted.
- B1 proposes unsafe steps in 9.6% of test episodes; it relies on the guard, which is part of the system.
- Scripted question counts are burden proxies; no user study was done.

## With more credits

- **Planned approach:** raise rollout diversity for GRPO (temperature 1.0+, mix in B0 rollouts, or rejection-sampled SFT variants) so groups differ in reward; fix the memory limit with batch 4 and gradient accumulation; target the two residual errors with step-level rewards; add Hindi/Hinglish paraphrases.
- **Expected before → after:** with non-zero reward variance, we expect eligible completion to rise from 53/68 toward the planner's 59/68 and unsafe-proposal episodes to fall from 23/240 toward under 10. This is a forecast, not a measurement.

## Artifacts

- **GitHub repo:** https://github.com/Pheonix-dev0410/lexsi-cybersos
- **HF datasets collection:** https://huggingface.co/collections/pgdev0410/cybersos-datasets-6af9f20f554b3a7be0d55145 (scenarios, curated decisions, evaluation traces)
- **HF models collection:** https://huggingface.co/collections/pgdev0410/cybersos-models-6af9f20ea81fe397ad74e7b4 (SFT LoRA adapter `pgdev0410/cybersos-tiny-aya-sft-lora`)
- **Demo / Space:** local Gradio app (`app.py`); not yet hosted.

## Documentation and reproduction

- **Environment:** Python 3.12, `pyyaml`, plus the pinned kits; training and inference need CUDA (L40S or better).
- **Repo layout and run instructions:** see `README.md` and `deploy/modal/README.md`. Modal jobs: `resolve_runtime`, `diagnose_base`, `render_training_file`, `train_sft`, `evaluate`, `train_agent`.
- **Work done outside the hackathon:** none. Everything was built during the hackathon.

## Teammates

- **Pranav Garg**: teacher and prompt design, SFT training and evaluation.
- **Rudr Pratap Singh**: recovery rules and sources from official help pages; scenario generation, root-level splits and leak checks; CuratorKIT curation and data gates.
- **Nikunj Kumar**: GPU compute and Modal infrastructure; baselines (Q, R) and AuditKIT scoring; AgentTune integration and GRPO runs.

## LLM usage statement

Approximately 90% of the code and 85% of this write-up were generated by AI coding assistants, working from a human-written project plan. Humans directed the project: problem choice, the model and compute decisions, and approval of each training and evaluation stage. All reported numbers come from logged runs in the linked repositories, not from model-written claims.

## References

Lexsi Labs kits (CuratorKIT, AlignTune, AgentTune, AuditKIT) at the pinned commits; Google Account Help pages listed in `data/sources.yaml`; `CohereLabs/tiny-aya-global` model card.
