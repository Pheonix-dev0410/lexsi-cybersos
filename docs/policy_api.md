# Policy API (rendering, serialization, serving contract, model policy)

| Name | Purpose |
|---|---|
| `render_observation` | Produce canonical unrendered role/content messages through closed schemas. |
| `serialize_prefix` | Apply the chat template once at the generation boundary. |
| `chat_template_sha256` | Hash of the template rendering uses (the named `default` one when a tokenizer ships several). |
| `export_sft_example`, `action_completion` | Export bounded SFT text with exactly one end token. |
| `POLICY`, `TOOLS_FALLBACK_PROMPT`, `TOOL_RESULT_FORMAT` | Versioned project prompts. |
| `TransformersPolicy` | Lazy, pinned, greedy inference with optional PEFT and run identity. |
| `snapshot_base_model` | Download an immutable revision and write its manifest. |
| `load_serving_contract`, `ServingContract`, `contract_hash` | Validate, freeze, hash, and key serving outputs. |
| `freeze_contract_pins` | Recompute the pinned corpus and guard hashes in the contract (`scripts/freeze_serving_contract.py`). |

All importable from `cybersos.policy`. Serving contract: `configs/baselines.yaml`.

The prompt is compact text so every decision fits the frozen 1,792-token prompt budget under
Tiny Aya's own template (about 400 tokens of preamble): tools as signatures generated from the
guard's action schema, one line per observed fact with its source and every earlier report, and
retrieved rules as `steps: prerequisites [source ids]` with shared prerequisites stated once.
Nothing observed is dropped; URLs and user-facing instructions stay in the application.

History renders each prior action as a call, `guard blocked: …` when the guard refused it, then
the observed result, including blocked actions. Model-written URLs in echoed proposals are replaced with a placeholder
(`cybersos.domain.sensitive_text.replace_urls`). Rules enter context only after retrieval;
rendering never reads hidden scenario data. Observations without `action_history` render
their result-only history.

`GenerationTimeout` extends `cybersos.runtime.PolicyTimeoutError`; the runner records
`timeout`. `PromptBudgetExceeded` extends `cybersos.runtime.PolicyBudgetExceeded`;
the runner ends with `budget_exhausted` without truncating facts or calling it a
generation error.
