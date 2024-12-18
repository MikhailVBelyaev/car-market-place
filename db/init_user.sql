CREATE USER marketplace_user WITH PASSWORD 'marketplace_user';
GRANT ALL PRIVILEGES ON SCHEMA marketplace TO marketplace_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA marketplace TO marketplace_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA marketplace TO marketplace_user;