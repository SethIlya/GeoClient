
FROM node:18-alpine as builder
WORKDIR /app/client

COPY client/package*.json ./

RUN npm install

COPY client/ ./

RUN npm run build

FROM python:3.10-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    netcat-traditional \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Создаем системного пользователя без прав администратора для безопасности
RUN addgroup --system app && adduser --system --group app

# Копируем скрипт запуска и даем ему права на выполнение
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /app

# Установка зависимостей Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код бэкенда
COPY . .

# --- КЛЮЧЕВОЙ ШАГ ---
# Копируем собранный фронтенд из первой стадии (builder)
# Это позволяет нам не хранить Node.js и все `node_modules` в финальном образе
COPY --from=builder /app/client/dist ./client/dist

# Меняем владельца всех файлов на нашего непривилегированного пользователя
RUN chown -R app:app /app
USER app

# Запускаем collectstatic. Django найдет статику Vue в ./client/dist
# и скопирует ее в STATIC_ROOT (/app/staticfiles)
RUN python manage.py collectstatic --noinput

# Открываем порт, на котором будет работать Gunicorn
EXPOSE 8000
<<<<<<< Updated upstream

# Указываем скрипт, который будет запущен при старте контейнера
ENTRYPOINT ["/entrypoint.sh"]
=======
ENTRYPOINT ["/app/entrypoint.sh"]

# Добавляем команду по умолчанию сюда:
CMD ["gunicorn", "app.wsgi:application", "--bind", "0.0.0.0:8000", "--user", "app", "--group", "app"]
>>>>>>> Stashed changes
