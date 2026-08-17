\set ON_ERROR_STOP on

-- Production reference only. Run as the PostgreSQL cluster administrator
-- against the target database, with database_name set explicitly. Passwords
-- must be injected by the secret manager and never committed or baked into an
-- image. The local Compose user is intentionally a development convenience.

\if :{?database_name}
\else
  \error 'database_name must be provided with --set=database_name=...'
\endif

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'curriculum_owner') THEN
        CREATE ROLE curriculum_owner NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'curriculum_migrator') THEN
        CREATE ROLE curriculum_migrator LOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'curriculum_runtime') THEN
        CREATE ROLE curriculum_runtime LOGIN;
    END IF;
END
$$;

-- The secret manager must supply these variables at invocation time.
\if :{?migrator_password}
ALTER ROLE curriculum_migrator PASSWORD :'migrator_password';
\else
  \error 'migrator_password must be supplied by the secret manager'
\endif
\if :{?runtime_password}
ALTER ROLE curriculum_runtime PASSWORD :'runtime_password';
\else
  \error 'runtime_password must be supplied by the secret manager'
\endif

GRANT curriculum_owner TO curriculum_migrator;
REVOKE ALL ON DATABASE :"database_name" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"database_name" TO curriculum_migrator, curriculum_runtime;

-- The following statements run after reconnecting to database_name. They are
-- kept here as a copy/paste-safe reference because psql cannot switch its
-- database connection inside a transaction.
\echo 'Reconnect to database_name, then run the schema privilege block below.'
\echo 'BEGIN;'
\echo 'ALTER SCHEMA public OWNER TO curriculum_owner;'
\echo 'REVOKE ALL ON SCHEMA public FROM PUBLIC;'
\echo 'GRANT USAGE ON SCHEMA public TO curriculum_runtime;'
\echo 'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO curriculum_runtime;'
\echo 'REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON TABLE identity_auditevent FROM curriculum_runtime;'
\echo 'GRANT SELECT, INSERT ON TABLE identity_auditevent TO curriculum_runtime;'
\echo 'GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO curriculum_runtime;'
\echo 'ALTER DEFAULT PRIVILEGES FOR ROLE curriculum_owner IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO curriculum_runtime;'
\echo 'ALTER DEFAULT PRIVILEGES FOR ROLE curriculum_owner IN SCHEMA public REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON TABLES FROM curriculum_runtime;'
\echo 'ALTER DEFAULT PRIVILEGES FOR ROLE curriculum_owner IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO curriculum_runtime;'
\echo 'GRANT USAGE, CREATE ON SCHEMA public TO curriculum_migrator;'
\echo 'COMMIT;'
