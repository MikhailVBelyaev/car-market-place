DO
$do$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'marketplace_user') THEN
    CREATE USER marketplace_user WITH PASSWORD 'marketplace_user';
  END IF;
END
$do$;
GRANT ALL PRIVILEGES ON SCHEMA marketplace TO marketplace_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA marketplace TO marketplace_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA marketplace TO marketplace_user;