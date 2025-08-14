#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Azure Ops Pack - Register Resource Providers

Registers required Azure resource provider namespaces and waits until Registered:
  - Microsoft.ContainerRegistry
  - Microsoft.App
  - Microsoft.OperationalInsights
  - Microsoft.KeyVault
  - Microsoft.DBforPostgreSQL
  - Microsoft.Cache
  - Microsoft.Network

Usage:
  bash scripts/azure/00_register_providers.sh

USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=./lib_common.sh
source "$SCRIPT_DIR/lib_common.sh"

ensure_logged_in

providers=(
  Microsoft.ContainerRegistry
  Microsoft.App
  Microsoft.OperationalInsights
  Microsoft.KeyVault
  Microsoft.DBforPostgreSQL
  Microsoft.Cache
  Microsoft.Network
)

info "Registering providers (idempotent)..."
for p in "${providers[@]}"; do
  info "- $p"
  az provider register --namespace "$p" --only-show-errors >/dev/null || true
done

info "Waiting for providers to be Registered..."
not_ready=("${providers[@]}")
for p in "${providers[@]}"; do
  if ! wait_provider_registered "$p"; then
    warn "Provider not registered after timeout: $p"
  fi
done

info "Provider registration states:"
az provider list --query "[?namespace=='Microsoft.ContainerRegistry' || namespace=='Microsoft.App' || namespace=='Microsoft.OperationalInsights' || namespace=='Microsoft.KeyVault' || namespace=='Microsoft.DBforPostgreSQL' || namespace=='Microsoft.Cache' || namespace=='Microsoft.Network'].[namespace,registrationState]" -o table

for p in "${providers[@]}"; do
  state=$(az provider show --namespace "$p" --query registrationState -o tsv 2>/dev/null || echo "Unknown")
  if [[ "$state" != "Registered" ]]; then
    die "Some providers not Registered: $p ($state)"
  fi
done

info "All providers Registered."

exit 0

#!/usr/bin/env bash
set -euo pipefail

# Registers required Azure resource providers for Forge 1
# Usage: bash scripts/azure/00_register_providers.sh

REQUIRED=(
  Microsoft.ContainerRegistry
  Microsoft.App
  Microsoft.OperationalInsights
  Microsoft.KeyVault
  Microsoft.DBforPostgreSQL
  Microsoft.Cache
  Microsoft.Network
)

echo "Registering Azure providers..."
for rp in "${REQUIRED[@]}"; do
  echo "az provider register --namespace $rp"
  az provider register --namespace "$rp" >/dev/null
done

echo "Waiting for providers to be Registered..."
deadline=$((SECONDS + 600))
while :; do
  all_ready=true
  for rp in "${REQUIRED[@]}"; do
    state=$(az provider show --namespace "$rp" --query "registrationState" -o tsv)
    echo "$rp: $state"
    if [[ "$state" != "Registered" ]]; then
      all_ready=false
    fi
  done
  if $all_ready; then
    echo "All providers Registered."
    break
  fi
  if (( SECONDS > deadline )); then
    echo "Timeout waiting for provider registrations" >&2
    exit 1
  fi
  sleep 10
done


