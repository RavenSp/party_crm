#!/usr/bin/env bash
# Точка входа контейнера party_crm: миграции, статика, gunicorn.
set -euo pipefail

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn --bind 0.0.0.0:8000 --workers "${GUNICORN_WORKERS:-3}" config.wsgi:application
