# Infrastructure

This directory contains infrastructure configuration and tooling for local development and deployment.

## Local Development

- `dev-check.sh`: Quick environment verification for local development
- `scripts/dev_env_check.sh`: Comprehensive development environment check script
- `.env.policy.md`: Environment variables and secrets management policy

## Cloud Infrastructure

- `azure/README.md`: Azure infrastructure planning and resource specifications

## Usage

### Quick Environment Check
```bash
./dev-check.sh
```

### Comprehensive Environment Check
```bash
./scripts/dev_env_check.sh
```

### Environment Policy
See `.env.policy.md` for detailed guidance on managing environment variables and secrets.

## Future Enhancements

- Docker and Kubernetes manifests
- GitHub Actions workflows
- Azure Key Vault integration
- Infrastructure as Code (Terraform/Bicep)
- Monitoring and alerting configuration


