#!/usr/bin/env bash
# Creates the local database, user and schema for Stage 1.
# Usage: ./scripts/setup_db.sh
set -euo pipefail

DB_NAME="${DB_NAME:-messages_db}"
DB_USER="${DB_USER:-messages_app}"
DB_PASSWORD="${DB_PASSWORD:-change_me_local}"

echo ">> creating database and user"
sudo -u postgres psql <<SQL
SELECT 'CREATE DATABASE ${DB_NAME}'
 WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_NAME}')\gexec

DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${DB_USER}') THEN
      CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';
   END IF;
END
\$\$;

GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
SQL

# Postgres 15+: database privileges no longer imply schema privileges.
# This line is the one everybody forgets.
sudo -u postgres psql -d "${DB_NAME}" -c "GRANT ALL ON SCHEMA public TO ${DB_USER};"

echo ">> applying schema"
PGPASSWORD="${DB_PASSWORD}" psql -h localhost -U "${DB_USER}" -d "${DB_NAME}" -f db/init.sql

echo ">> done"
