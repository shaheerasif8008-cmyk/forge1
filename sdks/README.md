# Forge 1 SDKs

Generated from the backend OpenAPI schema.

## TypeScript (ESM)

Install:

```bash
npm install @forge1/sdk
```

Usage:

```ts
import { Configuration, DefaultApi } from '@forge1/sdk';

const cfg = new Configuration({ basePath: process.env.FORGE1_API_URL });
const api = new DefaultApi(cfg);

// Auth via Bearer
const headers = { Authorization: `Bearer ${process.env.FORGE1_TOKEN}` };

// Create employee
await api.createEndpointEmployeesPost({ name: 'Agent', role_name: 'Sales', description: 'd', tools: [] } as any, { headers });

// Run task
const run = await api.executeEmployeeEmployeesEmployeeIdRunPost('employee-id', { task: 'Hello' } as any, { headers });
console.log(run.data.output);
```

## Python

Install:

```bash
pip install forge1-sdk
```

Usage:

```python
from forge1_sdk import Configuration, ApiClient, DefaultApi
import os

cfg = Configuration(host=os.getenv('FORGE1_API_URL'))
with ApiClient(cfg) as client:
    api = DefaultApi(client)
    headers={"Authorization": f"Bearer {os.getenv('FORGE1_TOKEN')}"}
    # Create employee
    api.create_endpoint_employees_post({"name":"Agent","role_name":"Sales","description":"d","tools":[]}, _headers=headers)
    # Run task
    res = api.execute_employee_employees_employee_id_run_post('employee-id', {"task":"Hello"}, _headers=headers)
    print(res.output)
```

## Generate SDKs locally

```bash
API_URL=http://localhost:8000/openapi.json ./scripts/sdk/gen_sdks.sh
```
