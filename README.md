# party_crm

CRM для партийной работы РПР (Российская рабочая партия) — Московская городская организация.

## Описание

Система учёта распространения партийной печати. Позволяет фиксировать:

- Где, когда и сколько газет распространялось
- Какие партийные члены и сочувствующие участвовали в распространении
- Сколько экземпляров было распространено на каждом предприятии
- Генерация отчётов в формате Excel по почте

## Технологии

- **Backend**: Django 4.2, Python
- **База данных**: PostgreSQL (psycopg3)
- **Frontend**: HTMX, Alpine.js, Bootstrap 5, Select2, jQuery
- **Отчёты**: XlsxWriter
- **Сервер**: Gunicorn

## Установка

### В Docker

Самый простой способ запустить CRM — Docker Compose (приложение + PostgreSQL):

1. Создайте файл окружения и заполните его:

```bash
cp .env.example .env
# отредактируйте .env: SECRET_KEY, DB_PASSWORD, ALLOWED_HOSTS, EMAIL_*
```

2. Соберите и запустите:

```bash
docker compose up --build -d
```

При старте контейнер сам применяет миграции и собирает статику
(см. `docker/entrypoint.sh`). CRM доступна на `http://localhost:8000`.

3. Создайте суперпользователя:

```bash
docker compose exec app python manage.py createsuperuser
```

Данные PostgreSQL хранятся в volume `pgdata`. Настройки контейнер читает из
переменных окружения (`.env`) через `config/docker_settings.py` — он
подключается автоматически, если нет `config/local_settings.py`.

### Для разработки

Быстрый способ — скрипт `setup.sh` (Debian/Ubuntu): установит системные пакеты,
PostgreSQL-пользователя и БД, venv с зависимостями, сгенерирует
`config/local_settings.py` (режим разработчика, `DEBUG=True`) и применит миграции:

```bash
./setup.sh          # или явно: ./setup.sh dev
```

Либо вручную:

1. Клонируйте репозиторий:

```bash
git clone <repository-url>
cd party_crm
```

2. Создайте виртуальное окружение и установите зависимости:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Создайте файл `config/local_settings.py` по шаблону и заполните его:

```bash
cp config/local_settings.example.py config/local_settings.py
# отредактируйте: SECRET_KEY, DATABASES, EMAIL_*, REPORT_MONTH_EMAIL
```

4. Выполните миграции:

```bash
python manage.py migrate
```

5. Создайте суперпользователя:

```bash
python manage.py createsuperuser
```

6. Запустите сервер разработки:

```bash
python manage.py runserver
```

### Для продакшена

Используйте prod-режим `setup.sh`:

```bash
APP_ALLOWED_HOSTS="crm.example.com,www.crm.example.com" ./setup.sh prod
```

Отличия от режима разработчика:

- `config/local_settings.py` генерируется с `DEBUG=False`, `ALLOWED_HOSTS`
  (из `APP_ALLOWED_HOSTS`, домены через запятую), `STATIC_ROOT` и
  HTTPS-hardening-настройками (`SECURE_SSL_REDIRECT`, secure-куки, HSTS —
  отключаются переменной `HTTPS=0`);
- выполняется `collectstatic` в `staticfiles/`;
- генерируются `deploy/gunicorn.conf.py` и `deploy/party-crm.service`
  (systemd-юнит с реальными путями; команды установки печатаются в конце
  скрипта, сам юнит скрипт не устанавливает).

После завершения: заполните `EMAIL_*` в `config/local_settings.py`, установите
systemd-юнит и настройте nginx как reverse proxy с TLS.

## Использование

### Авторизация

Вход в систему осуществляется по email (не по имени пользователя). Пароль задаётся при создании учётной записи.

### Основные разделы

- **Распространение** — создание и просмотр записей о распространении газет
- **Населённые пункты** — управление справочником населённых пунктов
- **Предприятия** — управление списком предприятий/точек распространения
- **Газеты** — каталог газет и их номеров
- **Отчёты** — генерация и отправка Excel-отчётов по почте

### Генерация отчётов

Отчёт можно сгенерировать двумя способами:

1. Через веб-интерфейс: перейдите в раздел `report/`
2. Через командную строку:

```bash
python manage.py send_report
```

Отчёт включает три листа:
- **Общие данные** — все распространения с датами, предприятиями, газетами и количеством
- **Распространители** — разбивка по каждому распространителю по месяцам
- **Предприятия** — разбивка по каждому предприятию по месяцам

## Структура проекта

```
party_crm/
├── config/              # Настройки Django, URL-маршруты, WSGI/ASGI
│   ├── settings.py      # Основные настройки
│   └── urls.py          # Корневой URL-конфиг
├── person/              # Пользовательская модель пользователя, аутентификация
│   ├── models.py        # Person (пользователь), PartyOrganization
│   └── views.py         # Вход, выход, профиль
├── press/               # Основная бизнес-логика
│   ├── models.py        # Newspaper, Town, FactoryPoint, Distribution и др.
│   ├── views.py         # CRUD распространений, отчёты, справочники
│   ├── services/        # Бизнес-логика: distributions, report, mail
│   └── management/      # Команды управления (send_report)
├── helpers/             # Вспомогательные утилиты (name_normalizer)
├── templates/           # Глобальные базовые шаблоны
└── static/              # Статические файлы (CSS, JS)
```

## Команды управления

```bash
# Запуск сервера разработки
python manage.py runserver

# Применение миграций
python manage.py migrate

# Создание суперпользователя
python manage.py createsuperuser

# Отправка месячного отчёта
python manage.py send_report

# Запуск тестов
python manage.py test
```

## Разработка

### Особенности

- Используется HTMX для динамического обновления страниц без перезагрузки
- HTMX-представления имеют префикс `hx_` в названиях методов
- Все пользовательские строки на русском языке (локаль `ru-ru`)
- Часовой пояс: `Europe/Moscow`

### Код-стайл

- Импорты: стандартная библиотека → Django → сторонние → локальные
- snake_case для функций/переменных, PascalCase для моделей
- URL: kebab-case с префиксами (`new-distrib/`, `hx-add-party-member/`)

## Лицензия

Проект распространяется под лицензией MIT. Подробности см. в файле [LICENSE](LICENSE).
