#!/bin/sh

# Выходим из скрипта, если любая команда завершится с ошибкой
set -e

# --- ДОБАВЛЕНО: Исправляем права на смонтированный том ---
# Эта команда выполняется от root и дает права пользователю app на папку
echo "Fixing media files ownership..."
chown -R app:app /app/mediafiles

echo "Waiting for PostgreSQL to start..."
# Проверяем доступность хоста и порта базы данных
while ! nc -z db 5432; do
  sleep 1
done
echo "PostgreSQL started"

# Применяем миграции базы данных. Можно выполнять от root.
echo "Applying database migrations..."
python manage.py migrate

echo "Starting Gunicorn server..."
# --- ИЗМЕНЕНИЕ: Запускаем Gunicorn, указывая ему сменить пользователя на 'app' ---
# 'exec' заменяет процесс shell на gunicorn
exec gunicorn app.wsgi:application --bind 0.0.0.0:8000 --user app --group app --timeout 300