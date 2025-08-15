# forge1-admin CLI

A Typer-based admin CLI for Forge 1.

## Install (local)

```bash
cd cli/forge1_admin
pip install -e .
```

## Usage

Set environment variables:

- `FORGE1_API_URL` (default `http://localhost:8000/api/v1`)
- `FORGE1_ADMIN_JWT` (admin bearer token)

```bash
forge1-admin --help

forge1-admin tenant:list
forge1-admin tenant:create "Acme Corp"
forge1-admin key:create <employee_id>
forge1-admin key:revoke <key_id>
forge1-admin flags:list --tenant-id <tenant>
forge1-admin flags:set router.force_provider_openai true --tenant-id <tenant>
forge1-admin runs:replay 42 --reason "fix policy" --policy '{"budget_per_day_cents": 500}'
```

Pretty tables and JSON output are rendered via `rich`.

## Publish (optional)

```bash
# Ensure you have a ~/.pypirc configured
cd cli/forge1_admin
python -m build
python -m twine upload dist/*
```


