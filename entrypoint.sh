#!/bin/sh

set -e

echo "Fixing media files ownership..."
chown -R app:app /app/mediafiles

echo "Waiting for PostgreSQL to start..."
while ! nc -z db 5432; do
  sleep 1
done
echo "PostgreSQL started"

echo "Applying database migrations..."
python manage.py migrate

# Важно: здесь должно быть exec "$@"
exec "$@" 