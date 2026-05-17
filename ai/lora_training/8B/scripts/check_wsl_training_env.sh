#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAINING_DIR="${TRAINING_DIR:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
CONDA_SH="${CONDA_SH:-${HOME}/miniconda3/etc/profile.d/conda.sh}"
ENV_NAME="${ENV_NAME:-clearread-llama-lora}"

source "${CONDA_SH}"
conda activate "${ENV_NAME}"
cd "${TRAINING_DIR}"

python scripts/check_wsl_training_env.py "$@"
