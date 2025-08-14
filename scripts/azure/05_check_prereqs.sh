#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Azure Ops Pack - Check Prerequisites

Verifies required CLI tools are installed and Azure login is active.

Checks:
  - az (Azure CLI)
  - docker
  - jq
  - psql (PostgreSQL client)
  - Azure login (az account show)

Usage:
  bash scripts/azure/05_check_prereqs.sh

USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

missing=()

need() {
  local bin="$1"
  if ! command -v "$bin" >/dev/null 2>&1; then
    missing+=("$bin")
  fi
}

need az
need docker
need jq
need psql

if (( ${#missing[@]} > 0 )); then
  echo "ERROR: Missing required tools: ${missing[*]}" >&2
  echo "Please install the missing tools and re-run."
  exit 1
fi

echo "All required tools found. Versions:"
echo "- az:     $(az version | jq -r '."azure-cli" // ."azure-cli-core" // "unknown"' 2>/dev/null || echo "unknown")"
echo "- docker: $(docker --version | sed 's/^Docker //')"
echo "- jq:     $(jq --version)"
echo "- psql:   $(psql --version)"

echo "Validating Azure login..."
if ! az account show >/dev/null 2>&1; then
  echo "ERROR: Azure CLI is not logged in. Run: az login" >&2
  exit 2
fi

SUB_NAME=$(az account show --query name -o tsv || echo "unknown-subscription")
echo "Azure login OK. Subscription: $SUB_NAME"

exit 0


