# Modal jobs

GPU stages run on Modal in the `nikunjkumar1405` workspace (it has GPU access), one H200 per training or evaluation job; student rollouts run as parallel L40S shards. Code and data are
mounted from this repository on every run; outputs go to the `cybersos-artifacts` volume.
The Hugging Face token comes from the Modal secret `cybersos-huggingface`. `run_job.sh` pins the workspace, so the active Modal profile does not matter.

```bash
deploy/modal/run_job.sh resolve_runtime --revision <hub commit>   # once: snapshot + contract values
deploy/modal/run_job.sh diagnose_base                               # B0 on the 36 diagnostic cases
deploy/modal/run_job.sh render_training_file
deploy/modal/run_job.sh train_sft --smoke                           # then --no-smoke
deploy/modal/run_job.sh evaluate --split dev --checkpoint base
deploy/modal/run_job.sh evaluate --split dev --checkpoint runs/sft-adapter --policy-label B1
MODAL_PROFILE=nikunjkumar1405 modal volume get cybersos-artifacts reports reports --force       # bring results back
```
