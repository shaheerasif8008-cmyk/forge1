## Deployment Runtime

The `DeploymentRuntime` accepts an employee config and prepares the orchestrator
and tools for execution.

### Expectations

- `role`, `tools`, `rag`, and `memory` sections must be present
- Tools referenced in `tools` must be available in the `ToolRegistry`
- If RAG is enabled but no retriever is provided, a no-op retriever is used

### Minimal usage

```python
rt = DeploymentRuntime(config)
orch = rt.build_orchestrator()
results = await rt.start("Initial task", iterations=1)
```


