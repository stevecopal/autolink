#!/bin/sh
set -e

echo "==> Waiting for PostgreSQL..."
while ! nc -z postgres_db 5432; do
  echo "    PostgreSQL not ready yet, retrying in 1s..."
  sleep 1
done
echo "==> PostgreSQL is up."

echo "==> Applying database migrations..."#!/bin/sh
set -e

# Utiliser les variables d'environnement si elles existent, sinon prendre des valeurs par défaut
DB_HOST="${SQL_HOST:-db}"
DB_PORT="${SQL_PORT:-5432}"

echo "==> Waiting for PostgreSQL on ${DB_HOST}:${DB_PORT}..."
while ! nc -z "$DB_HOST" "$DB_PORT"; do
  echo "    PostgreSQL not ready yet, retrying in 1s..."
  sleep 1
done
echo "==> PostgreSQL is up."

echo "==> Applying database migrations..."
python manage.py migrate --noinput

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Starting application..."
exec "$@"
python manage.py migrate --noinput

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Starting application..."
exec "$@"
