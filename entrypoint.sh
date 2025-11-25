#!/bin/sh

set -e

<<<<<<< Updated upstream
echo "Ожидание запуска PostgreSQL..."
# Проверяем доступность хоста 'db' и порта 5432
=======
echo "Fixing media files ownership..."
chown -R app:app /app/mediafiles

echo "Waiting for PostgreSQL to start..."
>>>>>>> Stashed changes
while ! nc -z db 5432; do
  sleep 1
done
echo "PostgreSQL запущен"

<<<<<<< Updated upstream
# Применяем миграции базы данных. Django создаст нужные таблицы.
echo "Применение миграций базы данных..."
python manage.py migrate

# Эта команда запустит ваше приложение.
# app.wsgi:application - указывает на объект application в файле app/wsgi.py
# --bind 0.0.0.0:8000 - Gunicorn будет слушать на порту 8000 внутри контейнера
echo "Запуск Gunicorn сервера..."
exec gunicorn app.wsgi:application --bind 0.0.0.0:8000
=======
echo "Applying database migrations..."
python manage.py migrate

# ВАЖНОЕ ИЗМЕНЕНИЕ:
# Эта команда означает "Выполни то, что передали в аргументах запуска Docker"
# Если аргументов нет, выполнится CMD из Dockerfile
exec "$@"
>>>>>>> Stashed changes
