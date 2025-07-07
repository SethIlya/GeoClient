# Dockerfile

# 1. Базовый образ с Python 3.10 на Debian (Linux)
FROM python:3.10-slim-bullseye

# Устанавливаем переменные окружения, чтобы Python не буферизовал вывод
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 2. Устанавливаем системные зависимости, необходимые для GeoDjango и PostgreSQL
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       libpq-dev \
       gdal-bin \
       libgdal-dev \
       proj-bin \
       libgeos-c1v5 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 3. Устанавливаем Gunicorn - наш production веб-сервер
RUN pip install gunicorn

# 4. Создаем рабочую директорию внутри контейнера
WORKDIR /app

# 5. Копируем файл с зависимостями и устанавливаем их
# Это делается отдельно, чтобы Docker мог кэшировать этот слой,
# и установка не повторялась каждый раз при изменении кода
COPY requirements.txt .
RUN pip install -r requirements.txt

# 6. Копируем весь остальной проект в рабочую директорию
COPY . .

# 7. Запускаем сборку статики Vue.js

# 8. Запускаем сборку статики Django
RUN python manage.py collectstatic --noinput

# 9. Открываем порт 8000, на котором будет работать gunicorn
EXPOSE 8000

# 10. Запускаем приложение
# Эта команда будет переопределена в docker-compose, но полезна как стандартная
CMD ["gunicorn", "app.wsgi:application", "--bind", "0.0.0.0:8000"]