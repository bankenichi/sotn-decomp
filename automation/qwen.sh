#!/usr/bin/env bash
# qwen.sh: zero-infrastructure fallback wrapper for the local model.
# Reads a system prompt file and a user prompt file, prints model output to stdout.
#
# Usage:   ./qwen.sh <system_prompt_file> <user_prompt_file>
# Env:     LLAMA_BASE_URL (default http://localhost:8080/v1), LLAMA_MODEL (default qwen)
#
# This is the Section 5.2 fallback from SOTN-Orchestration-Stack.md. Prefer the
# FastMCP server (mcp/sotn_local_mcp.py) for use inside Claude; use this script
# for shell pipelines and quick manual checks.
set -euo pipefail

base_url="${LLAMA_BASE_URL:-http://localhost:8080/v1}"
model="${LLAMA_MODEL:-qwen}"

if [ "$#" -ne 2 ]; then
  echo "usage: $0 <system_prompt_file> <user_prompt_file>" >&2
  exit 2
fi

payload="$(jq -n --rawfile sys "$1" --rawfile usr "$2" --arg model "$model" '{
  model: $model,
  temperature: 0.2,
  stream: false,
  messages: [
    {role: "system", content: $sys},
    {role: "user",   content: $usr}
  ]
}')"

curl -sS "${base_url%/}/chat/completions" \
  -H 'Content-Type: application/json' \
  -d "$payload" | jq -r '.choices[0].message.content'
