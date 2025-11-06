#!/bin/sh

# Выходим из скрипта, если любая команда завершится с ошибкой
set -e

echo "Ожидание запуска PostgreSQL..."
# Проверяем доступность хоста 'db' и порта 5432
while ! nc -z db 5432; do
  sleep 1
done
echo "PostgreSQL запущен"

# Применяем миграции базы данных. Django создаст нужные таблицы.
echo "Применение миграций базы данных..."
python manage.py migrate

# Эта команда запустит ваше приложение.
# app.wsgi:application - указывает на объект application в файле app/wsgi.py
# --bind 0.0.0.0:8000 - Gunicorn будет слушать на порту 8000 внутри контейнера
echo "Запуск Gunicorn сервера..."
exec gunicorn app.wsgi:application --bind 0.0.0.0:8000