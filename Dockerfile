# === СТАДИЯ 1: Сборка фронтенда (Vue.js) ===
FROM node:18-alpine as builder
WORKDIR /app/client

COPY client/package*.json ./
RUN npm install

COPY client/ ./
RUN npm run build


# === СТАДИЯ 2: Сборка бэкенда (Django) ===
FROM python:3.10-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Установка системных зависимостей
# ДОБАВЛЕНО: dos2unix - утилита, которая чинит Windows-переносы строк
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    netcat-traditional \
    dos2unix \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Создаем пользователя 'app'
RUN addgroup --system app && adduser --system --group app

WORKDIR /app

# 1. Сначала копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Копируем ВЕСЬ проект в папку /app
COPY . .

# 3. Копируем собранный фронтенд
COPY --from=builder /app/client/dist ./client/dist

# 4. Собираем статику
RUN python manage.py collectstatic --noinput

# 5. Настройка прав доступа и "ЛЕЧЕНИЕ" файла entrypoint.sh
# dos2unix принудительно меняет CRLF на LF, даже если Git испортил файл
RUN dos2unix /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Отдаем права пользователю app
RUN chown -R app:app /app

EXPOSE 8000

# Запускаем скрипт
ENTRYPOINT ["/app/entrypoint.sh"]

# Команда по умолчанию
CMD ["gunicorn", "app.wsgi:application", "--bind", "0.0.0.0:8000", "--user", "app", "--group", "app"]