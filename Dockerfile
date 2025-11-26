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

RUN addgroup --system app && adduser --system --group app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY --from=builder /app/client/dist ./client/dist

RUN python manage.py collectstatic --noinput

RUN dos2unix /app/entrypoint.sh && chmod +x /app/entrypoint.sh

RUN chown -R app:app /app

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]

CMD ["gunicorn", "app.wsgi:application", "--bind", "0.0.0.0:8000", "--user", "app", "--group", "app"]