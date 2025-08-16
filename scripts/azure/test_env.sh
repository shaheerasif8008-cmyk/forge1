#!/usr/bin/env bash
set -euo pipefail

# Simple test script to verify Azure environment setup

echo "============================================"
echo "Azure Environment Test"
echo "============================================"

# Check Azure CLI
if command -v az &>/dev/null; then
    echo "✓ Azure CLI installed"
    if az account show &>/dev/null; then
        echo "✓ Logged into Azure"
        ACCOUNT=$(az account show --query name -o tsv)
        echo "  Account: $ACCOUNT"
    else
        echo "✗ Not logged into Azure"
        echo "  Run: az login"
    fi
else
    echo "✗ Azure CLI not installed"
fi

# Check Docker
if command -v docker &>/dev/null; then
    echo "✓ Docker installed"
    if docker info &>/dev/null; then
        echo "✓ Docker daemon running"
    else
        echo "✗ Docker daemon not running"
    fi
else
    echo "✗ Docker not installed"
fi

# Check environment file
if [[ -f .azure/env.staging ]]; then
    echo "✓ Environment file exists"
    source .azure/env.staging
    echo "  Resource Group: ${RG:-<not set>}"
    echo "  Location: ${LOC:-<not set>}"
    echo "  Suffix: ${SUFFIX:-<not set>}"
    echo "  ACR: ${ACR:-<not set>}"
    echo "  Key Vault: ${KV:-<not set>}"
    echo "  ACA Environment: ${ACA_ENV:-${ACA_ENVIRONMENT:-<not set>}}"
else
    echo "✗ Environment file .azure/env.staging not found"
    echo "  Run: bash scripts/azure/10_bootstrap_core.sh"
fi

# Check Git
if command -v git &>/dev/null; then
    echo "✓ Git installed"
    if git rev-parse --git-dir &>/dev/null; then
        SHA=$(git rev-parse --short HEAD)
        echo "  Current SHA: $SHA"
    fi
else
    echo "✗ Git not installed"
fi

echo "============================================"