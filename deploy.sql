BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0a0d0717a24e

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE long_term_memory (
    id VARCHAR(100) NOT NULL, 
    content TEXT NOT NULL, 
    metadata JSONB DEFAULT '{}'::jsonb NOT NULL, 
    embedding VECTOR(1536), 
    created_at TIMESTAMP WITH TIME ZONE, 
    updated_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_ltm_embedding ON long_term_memory USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

INSERT INTO alembic_version (version_num) VALUES ('0a0d0717a24e') RETURNING alembic_version.version_num;

-- Running upgrade 0a0d0717a24e -> 0001_tenant

CREATE TABLE tenants (
    id VARCHAR(100) NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_tenants_id ON tenants (id);

-- Running upgrade 10_add_feature_flag_indexes -> 11_add_employee_keys

CREATE TABLE employee_keys (
    id VARCHAR(36) NOT NULL,
    tenant_id VARCHAR(100) NOT NULL,
    employee_id VARCHAR(100) NOT NULL,
    prefix VARCHAR(32) NOT NULL,
    hashed_secret VARCHAR(128) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    scopes JSON DEFAULT '{}'::json NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT employee_keys_pkey PRIMARY KEY (id),
    CONSTRAINT fk_empkey_tenant FOREIGN KEY(tenant_id) REFERENCES tenants (id),
    CONSTRAINT fk_empkey_employee FOREIGN KEY(employee_id) REFERENCES employees (id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX ix_employee_keys_prefix ON employee_keys (prefix);
CREATE INDEX ix_employee_keys_tenant_employee ON employee_keys (tenant_id, employee_id);

