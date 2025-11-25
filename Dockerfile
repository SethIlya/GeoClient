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
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    netcat-traditional \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Создаем пользователя 'app'
RUN addgroup --system app && adduser --system --group app

WORKDIR /app

# 1. Сначала копируем зависимости (для кэширования Docker слоев)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Копируем ВЕСЬ проект в папку /app
# В этот момент файл entrypoint.sh попадает в /app/entrypoint.sh
COPY . .

# 3. Копируем собранный фронтенд из первой стадии
COPY --from=builder /app/client/dist ./client/dist

# 4. Собираем статику (Django создает папку /app/staticfiles)
RUN python manage.py collectstatic --noinput

# 5. Настройка прав доступа и прав на выполнение скрипта
# Даем права на выполнение скрипту
RUN chmod +x /app/entrypoint.sh
# Отдаем все файлы пользователю app
RUN chown -R app:app /app

# ВАЖНО: Мы НЕ переключаемся на USER app здесь.
# Оставляем root, чтобы entrypoint.sh мог менять права на volume (mediafiles).
# Gunicorn сам сбросит права до app при запуске.

EXPOSE 8000

# Запускаем скрипт из папки /app
ENTRYPOINT ["/app/entrypoint.sh"]

# Команда по умолчанию (если не передана другая при запуске)
CMD ["gunicorn", "app.wsgi:application", "--bind", "0.0.0.0:8000", "--user", "app", "--group", "app"]