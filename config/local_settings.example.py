# Шаблон локальных настроек. Скопируйте в config/local_settings.py и заполните:
#   cp config/local_settings.example.py config/local_settings.py
# config/local_settings.py в .gitignore — не коммитить (секреты!).
# Быстрая альтернатива: ./setup.sh (dev) или ./setup.sh prod генерируют
# config/local_settings.py автоматически.
SECRET_KEY = 'your-secret-key-here'  # сгенерировать: python -c 'import secrets; print(secrets.token_urlsafe(50))'

DEBUG = True
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'party_crm_db',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Настройки почты для отправки отчётов
EMAIL_HOST = 'smtp.example.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'your-email@example.com'
EMAIL_HOST_PASSWORD = 'your-email-password'
EMAIL_USE_TLS = True

# Список получателей месячного отчёта
REPORT_MONTH_EMAIL = ['recipient@example.com']

# --- Продакшен (раскомментировать и заполнить) ---
# DEBUG = False
# ALLOWED_HOSTS = ['crm.example.com']
#
# from pathlib import Path
# STATIC_ROOT = Path(__file__).resolve().parent.parent / 'staticfiles'
#
# # HTTPS-hardening (при работе за TLS)
# SECURE_SSL_REDIRECT = True
# SECURE_HSTS_SECONDS = 15768000
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# SECURE_CONTENT_TYPE_NOSNIFF = True
