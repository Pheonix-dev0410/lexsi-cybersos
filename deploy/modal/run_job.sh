#!/bin/bash
# Runs one CyberSOS Modal job in the workspace that has GPU access, whatever profile is active.
# Detached, so a dropped laptop connection does not stop the job; outputs land on the volume.
# Usage: deploy/modal/run_job.sh <job> [job options], e.g. run_job.sh train_sft --no-smoke
set -euo pipefail
cd "$(dirname "$0")"
job="$1"; shift
MODAL_PROFILE=nikunjkumar1405 exec modal run --detach "cybersos_jobs.py::${job}" "$@"
