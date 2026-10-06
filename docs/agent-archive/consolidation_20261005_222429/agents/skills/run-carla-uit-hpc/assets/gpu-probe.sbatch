#!/bin/bash
# EXAMPLE ONLY, NOT A CARLA LAUNCHER. Read SKILL.md and UIT policy first.
# Replace <username>/<project>; verify permissions, quotas and own queue before submission.
# Pre-create /datastore/<username>/<project>/logs from login (file preparation).
# Explicit operator authorization is required; this file itself does not submit anything.
#SBATCH --job-name=uit_gpu_inventory
#SBATCH --account=uit
#SBATCH --partition=normal
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --time=01:00:00
#SBATCH --gres=gpu:2g.35gb:1
#SBATCH --chdir=/datastore/<username>/<project>
#SBATCH --output=/datastore/<username>/<project>/logs/inventory_%j.out
#SBATCH --error=/datastore/<username>/<project>/logs/inventory_%j.err

set -euo pipefail
if [[ -z "${SLURM_JOB_ID:-}" || -z "${SLURM_JOB_NODELIST:-}" ]]; then
  echo 'BLOCKED: inventory must run inside an authorized Slurm allocation' >&2
  exit 2
fi
actual_directory="$(pwd -P)"
case "$actual_directory" in
  /datastore/"$USER"|/datastore/"$USER"/*) ;;
  *) echo 'BLOCKED: working directory must be user Datastore' >&2; exit 2 ;;
esac
printf 'job_id=%s nodes=%s assigned_devices=%s\n' "$SLURM_JOB_ID" "$SLURM_JOB_NODELIST" "${CUDA_VISIBLE_DEVICES:-unknown}"
uname -m
grep '^PRETTY_NAME=' /etc/os-release
# Bounded inventory only, in own allocation, never from login or direct SSH to GPU node.
timeout 15s nvidia-smi -L
# No CARLA/Vulkan launch: current documented profiles are MIG. Ask administrators first.
