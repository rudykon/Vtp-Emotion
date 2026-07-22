#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ID="${1:-${MERPS_EXTERNAL_REPO_ID:-}}"
DEST_DIR="${2:-$PROJECT_ROOT/data/download/MER_PS_public_evaluation}"
TOKEN_FILE="${HUGGINGFACE_TOKEN_FILE:-$PROJECT_ROOT/huggingface_token.json}"

if [[ -z "$REPO_ID" ]]; then
  echo "Usage: MERPS_EXTERNAL_REPO_ID=<dataset-repository> bash scripts/download_external_data.sh" >&2
  exit 2
fi
if [[ ! -f "$TOKEN_FILE" ]]; then
  echo "Missing Hugging Face token file: $TOKEN_FILE" >&2
  exit 3
fi

if [[ -x "$PROJECT_ROOT/.venv/bin/hf" ]]; then
  HF_CLI=("$PROJECT_ROOT/.venv/bin/hf" download)
elif command -v hf >/dev/null 2>&1; then
  HF_CLI=(hf download)
else
  echo "The Hugging Face CLI is required. Install huggingface_hub[hf_xet] first." >&2
  exit 127
fi

HF_TOKEN="$(jq -r '.huggingface_token // empty' "$TOKEN_FILE")"
if [[ -z "$HF_TOKEN" ]]; then
  echo "The token file does not contain a non-empty huggingface_token field." >&2
  exit 4
fi

mkdir -p "$DEST_DIR"
export HF_TOKEN
export HF_XET_HIGH_PERFORMANCE=1

"${HF_CLI[@]}" "$REPO_ID" \
  --repo-type dataset \
  --local-dir "$DEST_DIR" \
  --max-workers 4 \
  --format agent

echo "External evaluation data saved under: $DEST_DIR"
