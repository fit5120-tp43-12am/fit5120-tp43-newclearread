#!/usr/bin/env bash
set -euo pipefail

TRAINING_DIR="/mnt/c/Users/Aufb/Desktop/fit5120/iteration1/training"
CONDA_SH="/home/aufb/miniconda3/etc/profile.d/conda.sh"
ENV_NAME="clearread-llama-lora"

source "${CONDA_SH}"
conda activate "${ENV_NAME}"
cd "${TRAINING_DIR}"

python scripts/check_wsl_training_env.py "$@"
