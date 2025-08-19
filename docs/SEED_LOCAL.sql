-- Seed minimal data for local development
INSERT INTO tenants (id, name, beta, created_at)
VALUES ('t-local', 'Local Tenant', false, NOW())
ON CONFLICT (id) DO NOTHING;

-- Optional: create an admin user placeholder if schema supports it
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='users') THEN
    INSERT INTO users (email, username, hashed_password, is_active, is_superuser, role, created_at)
    VALUES ('admin@example.com', 'admin', 'change-me', true, true, 'admin', NOW())
    ON CONFLICT DO NOTHING;
  END IF;
END$$;

-- Seed demo data for Local Mode
-- Safe to run multiple times (uses upserts where applicable)

-- Tenants
INSERT INTO tenants (id, name, beta, created_at, updated_at)
VALUES ('default', 'Default Tenant', false, NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;

-- Users (password hash not needed for demo login route; kept for completeness)
INSERT INTO users (id, email, username, hashed_password, is_active, is_superuser, role, tenant_id, created_at, updated_at)
VALUES (1, 'admin@example.com', 'admin', '$2b$12$abcdefghijklmnopqrstuv', true, true, 'admin', 'default', NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email;

-- Employees
INSERT INTO employees (id, tenant_id, owner_user_id, name, config, created_at, updated_at)
VALUES ('demo-writer', 'default', 1, 'Demo Writer', '{"role": "writer", "tools": []}'::jsonb, NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;

-- TaskExecutions
INSERT INTO task_executions (tenant_id, employee_id, user_id, task_type, prompt, response, model_used, tokens_used, execution_time, success, error_message, cost_cents, task_data, created_at)
VALUES
('default', 'demo-writer', 1, 'write', 'Hello', 'World', 'openai:gpt-4o-mini', 256, 800, true, NULL, 2, '{}', NOW() - INTERVAL '2 days'),
('default', 'demo-writer', 1, 'write', 'Foo', 'Bar', 'openai:gpt-4o-mini', 300, 1000, false, 'timeout', 3, '{}', NOW() - INTERVAL '1 days'),
('default', 'demo-writer', 1, 'write', 'Baz', 'Qux', 'openai:gpt-4o-mini', 210, 700, true, NULL, 2, '{}', NOW() - INTERVAL '12 hours');

-- Audit logs
INSERT INTO audit_logs (tenant_id, user_id, action, method, path, status_code, timestamp, meta)
VALUES
('default', 1, 'http_request', 'GET', '/api/v1/health', 200, NOW() - INTERVAL '1 hour', '{"trace_id":"seed"}'),
('default', 1, 'http_request', 'POST', '/api/v1/ai/execute', 200, NOW() - INTERVAL '30 minutes', '{"trace_id":"seed2"}');


