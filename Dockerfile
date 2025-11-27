# Переименуй этот файл в Dockerfile.backend или оставь Dockerfile, но измени содержимое:

FROM python:3.10-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev gdal-bin libgdal-dev netcat-traditional dos2unix \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN addgroup --system app && adduser --system --group app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Собираем статику 
RUN python manage.py collectstatic --noinput

RUN dos2unix /app/entrypoint.sh && chmod +x /app/entrypoint.sh
RUN chown -R app:app /app

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "app.wsgi:application", "--bind", "0.0.0.0:8000", "--user", "app", "--group", "app"]