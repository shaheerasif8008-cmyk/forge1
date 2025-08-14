#!/usr/bin/env bash
set -euo pipefail

# Common helpers for Azure Ops Pack scripts

die() { echo "ERROR: $*" >&2; exit 1; }
info() { echo "[INFO] $*"; }
warn() { echo "[WARN] $*" >&2; }

ensure_cmd() {
  local bin
  for bin in "$@"; do
    command -v "$bin" >/dev/null 2>&1 || die "Missing required command: $bin"
  done
}

prompt_secret() {
  # usage: prompt_secret VAR_NAME "Prompt message"
  local var_name="$1"; shift
  local prompt_msg="$1"; shift || true
  local current_val="${!var_name:-}"
  if [[ -z "$current_val" ]]; then
    read -r -s -p "$prompt_msg: " current_val; echo
  fi
  [[ -n "$current_val" ]] || die "$var_name cannot be empty"
  printf -v "$var_name" '%s' "$current_val"
}

gen_suffix() {
  # 5-char [a-z0-9] suffix, safe for zsh/bash
  LC_ALL=C tr -dc 'a-z0-9' </dev/urandom | head -c 5
}

read_env() {
  # Source .azure/env.staging if present
  if [[ -f .azure/env.staging ]]; then
    # shellcheck source=/dev/null
    source .azure/env.staging
  fi
}

ensure_logged_in() {
  az account show >/dev/null 2>&1 || die "Not logged in to Azure. Run 'az login'"
}

kv_set_secret() {
  # kv_set_secret <vault> <name> <value>
  local vault="$1"; local name="$2"; local value="$3"
  [[ -n "$vault" && -n "$name" && -n "$value" ]] || die "kv_set_secret requires non-empty vault, name, and value"
  az keyvault secret set --vault-name "$vault" --name "$name" --value "$value" -o none
}

wait_provider_registered() {
  # wait_provider_registered <namespace>
  local ns="$1"; local max_secs=$((10*60)); local interval=10; local elapsed=0
  while (( elapsed < max_secs )); do
    local state
    state=$(az provider show --namespace "$ns" --query registrationState -o tsv 2>/dev/null || echo "Unknown")
    if [[ "$state" == "Registered" ]]; then
      return 0
    fi
    sleep "$interval"; elapsed=$((elapsed+interval))
  done
  return 1
}


