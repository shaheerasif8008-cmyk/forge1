#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Azure Ops Pack - Cleanup (DANGER)

Deletes the resource group defined in .azure/env.staging after confirmation.

Usage:
  bash scripts/azure/99_cleanup.sh
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

[[ -f .azure/env.staging ]] || { echo "ERROR: .azure/env.staging not found." >&2; exit 2; }
source .azure/env.staging

echo "This will DELETE resource group '$RG' in location '$LOC'."
read -r -p "Type DELETE to confirm: " CONFIRM
if [[ "$CONFIRM" != "DELETE" ]]; then
  echo "Aborted."
  exit 1
fi

echo "Deleting resource group $RG ..."
az group delete -n "$RG" --yes --no-wait
echo "Deletion requested. Resources will be removed asynchronously."

exit 0


