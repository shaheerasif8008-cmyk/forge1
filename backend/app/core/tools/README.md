## Tools

Tools are modular actions the agent can execute.

### BaseTool contract

- Inherit from `BaseTool`
- Implement `execute(**kwargs) -> Any`
- Provide class attributes `name: str` and `description: str`

`run(**kwargs)` is provided for registry compatibility and delegates to `execute`.

### Creating a new tool

1. Add a module under `core/tools/builtins/` or a separate package
2. Export your instance through a `TOOLS` dict: `{ToolClass.name: ToolClass()}`
3. Keep heavy imports inside `execute()` and raise a helpful `RuntimeError` if missing
4. The `ToolRegistry` can auto-discover built-ins and will register them


