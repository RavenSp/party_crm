# Образ party_crm: Django + gunicorn. Запуск — через docker-compose.yml.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Зависимости отдельным слоем, чтобы кэшировались при изменении кода
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

ENTRYPOINT ["docker/entrypoint.sh"]
