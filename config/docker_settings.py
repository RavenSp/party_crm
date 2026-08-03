# Настройки из переменных окружения для запуска в Docker.
# Подключается из config/settings.py, если нет config/local_settings.py.
# Значения задаются через .env (см. .env.example) или окружение контейнера.
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


def _env(name, default=None, required=False):
    """Читает переменную окружения; для обязательных бросает понятную ошибку."""
    value = os.environ.get(name, default)
    if required and not value:
        raise ImproperlyConfigured(
            f'Переменная окружения {name} не задана. '
            f'Заполните .env по образцу .env.example'
        )
    return value


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = _env('SECRET_KEY', required=True)

DEBUG = _env('DEBUG', '0') == '1'

ALLOWED_HOSTS = _env('ALLOWED_HOSTS', 'localhost').split(',')

STATIC_ROOT = BASE_DIR / 'staticfiles'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': _env('DB_NAME', 'party_crm_db'),
        'USER': _env('DB_USER', 'party_crm'),
        'PASSWORD': _env('DB_PASSWORD', required=True),
        'HOST': _env('DB_HOST', 'db'),
        'PORT': _env('DB_PORT', '5432'),
    }
}

# Настройки почты для отправки отчётов
EMAIL_HOST = _env('EMAIL_HOST', 'smtp.example.com')
EMAIL_PORT = int(_env('EMAIL_PORT', '587'))
EMAIL_HOST_USER = _env('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = _env('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = _env('EMAIL_USE_TLS', '1') == '1'

# Список получателей месячного отчёта, адреса через запятую
REPORT_MONTH_EMAIL = [
    addr.strip()
    for addr in _env('REPORT_MONTH_EMAIL', '').split(',')
    if addr.strip()
]

# HTTPS-hardening: HTTPS=1 включает те же настройки, что и setup.sh prod
SECURE_CONTENT_TYPE_NOSNIFF = True
if _env('HTTPS', '0') == '1':
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 15768000
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
