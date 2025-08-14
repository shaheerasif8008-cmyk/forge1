# Forge 1 Shared Package

Shared utilities and synthetic testing harness for the Forge 1 monorepo. This package is consumed by both the production backend and the testing-app to avoid duplication and ensure consistent test semantics.

## What is included

- `shared.testing.schemas`: Pydantic models for test suites and reports
- `shared.testing.runner`: YAML loader and suite runner with injectable execution hooks
- `shared.testing.suites`: Built-in example YAML suites (`golden_basic.yaml`, `adversarial.yaml`, `cost_latency.yaml`)
- `shared.utils`: Small utilities used by the runner

## Installation (editable)

Recommended for local development to keep changes live without reinstalling.

```bash
# From repository root
cd shared
python -m venv .venv && source .venv/bin/activate  # or use your existing env
pip install -U pip
pip install -e .[dev]
```

To use the shared package from the production backend or testing-app environments:

```bash
# In backend venv
pip install -e ../shared

# In testing-app venv (when created)
pip install -e ../shared
```

## Usage

```python
from shared.testing.runner import load_suite_from_name, run_suite

suite = load_suite_from_name("golden_basic.yaml")

def execute_case(case, hooks=None):
    # Your app-specific logic here
    # Return a CaseResult
    ...

report = run_suite(suite, execute_case)
print(report.metrics)
```

## Adding a new suite

1. Create a new YAML file under `shared/testing/suites/` (e.g., `my_suite.yaml`).
2. Follow the schema in `shared/testing/schemas.py` (`TestSuite` and `TestCase`).
3. Validate locally:

```bash
pytest -q shared/tests
```

## License

MIT


