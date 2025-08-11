## Employee Builder

The Employee Builder produces validated, deployment-ready employee configuration
objects that can be consumed by the runtime.

### Config shape

```
{
  "role": {
    "name": "Research Assistant",
    "description": "Conducts literature reviews and summarizes findings"
  },
  "tools": [
    {"name": "web_scraper", "config": {"max_depth": 2}},
    {"name": "doc_summarizer", "config": {}}
  ],
  "rag": {"enabled": true, "top_k": 5, "provider": "hybrid"},
  "memory": {
    "short_term": {"provider": "redis", "ttl": 3600},
    "long_term": {"provider": "pgvector", "dimensions": 1536}
  }
}
```

Templates can add `required_tools` that will be merged with user-provided tools.

### Adding a template

1. Create a JSON or YAML file in `core/employee_builder/templates/`
2. Include `role.description`, optional `required_tools`, `rag`, and `memory`
3. Name the file to match the role (e.g., `sales_agent.json`)
4. The builder will infer the template from role name or you can pass `template_name`


