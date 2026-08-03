# AGENTS.md — party_crm

Этот файл предназначен для AI-агентов, работающих с кодовой базой. Здесь собраны сведения об архитектуре, командах, соглашениях и известных проблемах проекта. Предполагается, что читатель ничего не знает о проекте.

## Обзор проекта

CRM для партийной работы РПР (Российская рабочая партия) — Московская городская организация. Система учёта распространения партийной печати: фиксирует, где, когда и сколько газет роздано, кто из членов партии и сочувствующих участвовал в раздаче, и формирует Excel-отчёты с отправкой по email.

**Технологический стек:**
- Backend: Django 4.2 (Python), Gunicorn для production
- База данных: PostgreSQL (драйвер psycopg 3, пакет `psycopg[binary]`)
- Frontend: HTMX (django-htmx), Alpine.js, Bootstrap 5, Select2, jQuery — всё лежит локально в `static/`
- Отчёты: XlsxWriter
- Статика в production: WhiteNoise (middleware в `config/settings.py`)
- Контейнеризация: Dockerfile + docker-compose.yml (app + PostgreSQL)
- Шаблоны: Django Templates + `django-render-block` (частичный рендеринг блоков) + `django-widget-tweaks`

Зависимости — только в `requirements.txt` (без pyproject.toml/poetry). Конфигурационных файлов сборки (package.json, Cargo.toml и т.п.) нет; `package.json` и `node_modules` явно добавлены в `.gitignore`.

**Excel-отчёт** (`press/services/report.py`, `generate_report()`) содержит три листа:
1. «Общие данные» — все раздачи: даты, предприятия, газеты, количества;
2. «Распространители» — помесячная разбивка по людям;
3. «Предприятия» — помесячная разбивка по предприятиям.

Генерируется через веб-форму (`report/`, отправка на email) или командой `python manage.py send_report` (требует `REPORT_MONTH_EMAIL`).

## Структура проекта

```
party_crm/
├── config/                  # Настройки проекта Django
│   ├── settings.py          # Основные настройки; в конце: local_settings, иначе docker_settings
│   ├── docker_settings.py   # Настройки из переменных окружения (Docker, .env)
│   ├── local_settings.example.py  # Шаблон локальных настроек (копируется в local_settings.py)
│   ├── urls.py              # Корневой URLconf: admin, login, press (корень), person (profile/)
│   └── wsgi.py / asgi.py
├── person/                  # Приложение: пользователи и аутентификация
│   ├── models.py            # Person (AUTH_USER_MODEL, AbstractUser, USERNAME_FIELD='email'), PartyOrganization
│   ├── managers.py          # CustomUserManager (create_user/create_superuser по email)
│   ├── services/login.py    # auth_user() — аутентификация по email+пароль
│   ├── signals.py           # СЛОМАН: сигналы на django.contrib.auth.models.User, который не используется
│   ├── urls.py              # profile (''), hx-login, logout/
│   └── views.py             # login, logout_view, profile
├── press/                   # Приложение: основная бизнес-логика
│   ├── models.py            # Newspaper, NewspaperNumber, Sympathizer, Town, FactoryPoint,
│   │                        # Distribution, NewspaperNumbersOnDistribution,
│   │                        # DistributionPartyMembers, DistributionSympathizerMember
│   ├── forms.py             # DistributionForm, FabricForm (FactoryPoint), NewspapersNumberForm
│   ├── views.py             # Все view: список раздач, создание раздачи, справочники, отчёты
│   ├── services/            # Слой бизнес-логики:
│   │   ├── distributions.py # get_all(filter_by) — выборка раздач с prefetch_related
│   │   ├── factory.py       # get_all(filter_by) для предприятий
│   │   ├── newspaper.py     # CRUD-функции для газет (add/edit/get)
│   │   ├── report.py        # generate_report() — Excel-отчёт через xlsxwriter в BytesIO
│   │   └── mail.py          # send_report() — отправка отчёта через EmailMultiAlternatives
│   ├── management/commands/send_report.py  # Команда отправки месячного отчёта
│   └── templates/press/     # Шаблоны приложения
├── helpers/common.py        # name_normalizer() — нормализация имён (убирает пробелы/знаки, lower)
├── setup.sh                 # Развёртывание на новой системе (пакеты, PostgreSQL, venv, local_settings); режимы dev/prod
├── Dockerfile               # Образ приложения (python:3.12-slim, gunicorn)
├── docker-compose.yml       # Запуск в Docker: сервисы app (gunicorn) и db (postgres:16-alpine, volume pgdata)
├── docker/entrypoint.sh     # Точка входа контейнера: migrate → collectstatic → gunicorn
├── .env.example             # Образец переменных окружения для Docker (копируется в .env)
├── .dockerignore            # Исключения контекста сборки (venv, .env, local_settings.py и т.п.)
├── deploy/                  # Генерируется `setup.sh prod` (gunicorn.conf.py, party-crm.service); в .gitignore
├── templates/               # Глобальные шаблоны: base.html, login.html, меню, error_alert.html
├── static/                  # css/, js/ (htmx, alpine, bootstrap, select2, jquery), service-worker.js
├── docs/
│   ├── src/                 # MkDocs-документация для пользователей (mkdocs.yml + docs/*.md)
│   └── django_and_database.md  # Автогенерируемый файл (в .gitignore), не редактировать
└── requirements.txt
```

## Модели данных (кратко)

- **Person** (`person`) — пользователь. `username = None`, вход по `email`. Поля: `party_member` (bool), `party_ticket_number`, `party_organization` (FK), `bio`. Свойство `full_name`.
- **Newspaper / NewspaperNumber** — газета и её конкретный номер (`number`, `year` — DateField «год и месяц выхода»).
- **Town** → **FactoryPoint** — населённый пункт и предприятие/точка раздачи (с гео-координатами `geo_lat`/`geo_lon`).
- **Sympathizer** — сочувствующий (не член партии), только `name`. Дедупликация по свойству `normalize_name`.
- **Distribution** — событие раздачи: дата, время начала/конца, `autor` (FK Person, опечатка в имени поля!), `factory` (FK).
- **NewspaperNumbersOnDistribution**, **DistributionPartyMembers**, **DistributionSympathizerMember** — строки раздачи: сколько каких номеров роздано и кем (related_name: `numbers`, `party_members`, `sympathizer_members`).

## Команды

```bash
# Развёртывание на новой системе (Debian/Ubuntu): пакеты, PostgreSQL (пользователь
# и БД), venv + зависимости, config/local_settings.py, миграции, правила Kimi Code.
# Два режима: dev (по умолчанию, DEBUG=True) и prod (DEBUG=False, ALLOWED_HOSTS из
# APP_ALLOWED_HOSTS, STATIC_ROOT + collectstatic в staticfiles/, HTTPS-hardening
# (отключается HTTPS=0), генерация deploy/gunicorn.conf.py и deploy/party-crm.service).
# Флаги: SKIP_PACKAGES, SKIP_POSTGRES, SKIP_VENV, SKIP_MIGRATE, INSTALL_KIMI_ALLOW=1|0
# Параметры prod: APP_ALLOWED_HOSTS="домены,через,запятую", HTTPS=1|0
./setup.sh          # или ./setup.sh dev — для разработчика
./setup.sh prod     # для запуска CRM в продакшене

# Ручная установка (виртуальное окружение)
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Перед первым запуском: создать config/local_settings.py (setup.sh копирует
# config/local_settings.example.py и подставляет SECRET_KEY и параметры БД
# автоматически): SECRET_KEY, DATABASES (PostgreSQL),
# EMAIL_*, REPORT_MONTH_EMAIL. Файл в .gitignore, шаблон-пример — в репозитории

python manage.py migrate           # Миграции
python manage.py createsuperuser   # Суперпользователь (по email)
python manage.py runserver         # Сервер разработки
python manage.py test              # Тесты (требует рабочий PostgreSQL из local_settings.py)
python manage.py send_report       # Отправка Excel-отчёта на REPORT_MONTH_EMAIL
```

Запуск в Docker:

```bash
cp .env.example .env               # заполнить SECRET_KEY, DB_PASSWORD, EMAIL_*
docker compose up --build -d       # приложение + PostgreSQL, миграции и статика — при старте
docker compose exec app python manage.py createsuperuser
docker compose logs -f app         # логи приложения
docker compose down                # остановка (данные БД остаются в volume pgdata)
```

Production: Gunicorn (`requirements.txt`), WSGI — `config/wsgi.py`. Развёртывание — `./setup.sh prod` (генерирует systemd-юнит `deploy/party-crm.service`, установка вручную). CI в репозитории нет.

Документация для пользователей — MkDocs (`docs/src/mkdocs.yml`), собирается стандартно (`mkdocs build` из `docs/src/`), тема `mkdocs`, язык `ru`.

## Разрешённые команды

AI-ассистенту разрешено выполнять без дополнительного подтверждения:

- **Проверки и тесты Django:** `python manage.py check`, `python manage.py test`, `python manage.py showmigrations`, `python manage.py makemigrations` (создаёт только файлы миграций).
- **Запуск сервера разработки:** `python manage.py runserver`.
- **Git только на чтение:** `git status`, `git diff`, `git log`, `git show`, `git branch`.
- **Окружение и процессы (только чтение):** `which`, `ls`, `grep`, `ps aux`.

Всё остальное выполнять только после явного подтверждения пользователя:

- прямые `git commit` / `git push` / `git reset` / `git rebase` и другие изменения репозитория;
- `python manage.py migrate` (меняет состояние базы данных);
- `python manage.py send_report` (отправляет реальные письма на `REPORT_MONTH_EMAIL`);
- `python manage.py createsuperuser` и другие команды, создающие/меняющие данные;
- удаление файлов, установка пакетов, операции вне каталога проекта.

Команды из первого списка `setup.sh` умеет автоматически добавлять в `config.toml` Kimi Code как правила `[[permission.rules]]` с `decision = "allow"` (шаг 7, спрашивает при установке или управляется переменной `INSTALL_KIMI_ALLOW`). Блок правил помечен маркерами `# party-crm:`, поэтому при повторном запуске `setup.sh` он заменяется целиком, а не дублируется. При изменении этого списка обновляйте и шаг 7 в `setup.sh`, чтобы списки не расходились.

## URL-маршруты

Корневой `config/urls.py`: `admin/`, `login/` (person.views.login), `profile/` → `person.urls`, остальное → `press.urls` (корень сайта). Также подключён `django.contrib.auth.urls`.

`press/urls.py`:
| Путь | View | Назначение |
|---|---|---|
| `''` | `my_distribution` | Список раздач за последние 31 день (GET/POST-фильтр, HTMX) |
| `new-distrib/` | `new_distrib` | Создание раздачи |
| `hx-distrib/<pk>/` | `hx_distrib` | Удаление раздачи (HTMX) |
| `hx-newspaper-field/` | `hx_newspaper` | Динамическое поле выбора газеты |
| `report/` | `report_generate` | Форма генерации и отправки отчёта |
| `towns/`, `towns/<pk>/` | `towns`, `towns_delete` | Справочник городов |
| `factory/` | `factory` | CRUD предприятий (GET/POST/DELETE в одном view) |
| `newspaper/`, `newspaper-numbers/` | `newspaper`, `newspaper_numbers` | Справочники газет и номеров |
| `htmx-add-party-member/`, `htmx-add-sympathizer/`, `hx-add-party-member/`, `hx-delete-pary-member/` | — | **DEPRECATED**, не использовать |

`person/urls.py` (под `profile/`): `''` → profile, `hx-login`, `logout/`.

## Соглашения по коду

- **Язык**: все пользовательские строки, `verbose_name`, комментарии и документация — на русском. Локаль `ru-ru`, часовой пояс `Europe/Moscow` (`USE_TZ = True`). Сообщения коммитов в истории смешанные (русский и английский); не упоминать тесты в сообщениях коммитов; писать кратко и о «почему», а не о «что».
- **Типизация**: type hints применяются непоследовательно; в слое services — частично.
- **Импорты**: стандартная библиотека → Django → сторонние → локальные.
- **Именование**: snake_case для функций/переменных, PascalCase для моделей, kebab-case для URL.
- **HTMX**: HTMX-эндпоинты именуются с префиксом `hx_`. Для частичного рендеринга используется `render_block_to_string()` (django-render-block), для смены цели — `retarget()` (django-htmx). Ошибки форм показываются через `templates/error_alert.html` с ретаргетом в `#modal-alert`.
- **Все view** защищены `@login_required()`; `LOGIN_URL = '/login/'`.
- **Бизнес-логика** частично вынесена в `*/services/`, но значительная часть остаётся во views (например, `new_distrib` ~90 строк со вложенной логикой распределения количества газет между раздающими). При доработках предпочтительно выносить логику в services.
- **Запросы**: в сервисных функциях принят паттерн `get_all(filter_by)` с `filter(**filter_by)` и `select_related`/`prefetch_related`.
- **Формы**: ModelForm'ы в `press/forms.py`; POST-данные для динамических списков (газеты, раздающие) читаются напрямую через `request.POST.getlist()`.

## Тестирование

- Запуск: `./run_tests.sh` — сам поднимает временный PostgreSQL-инстанс в `/tmp` (без sudo и системной БД, ищет бинарники в `/usr/lib/postgresql/*/bin`), прогоняет тесты и удаляет инстанс; флаг `--coverage` — измерение покрытия. `python manage.py test` напрямую требует рабочий PostgreSQL из `local_settings.py`.
- Фреймворк — стандартный `django.test.TestCase`, pytest не используется. Отдельного settings-модуля для тестов нет; Django сам подменяет `EMAIL_BACKEND` на locmem при прогоне тестов.
- Покрытие: `person/tests.py` (менеджер, модели, формы, view, сервис `auth_user`), `press/tests.py` (модели, формы, сервисы `distributions/factory/newspaper/report/mail`, все view включая deprecated и HTMX-ветки, management-команда `send_report`), `helpers/tests.py` (`name_normalizer`).
- Измерение покрытия: `coverage run manage.py test && coverage report -m` (конфиг — `.coveragerc`: source = person/press/helpers, исключены миграции, тесты, config, `person/signals.py`). Текущее покрытие — 100% строк; недостижимые из-за известных багов ветки помечены `# pragma: no cover` с пояснением.
- Тесты на известные баги оформляются как «фиксирует текущее поведение» (assertRaises/фактический результат + поясняющий docstring), без исправления кода.
- При добавлении логики в `press` (views, services, forms) новые тесты писать в `press/tests.py` в стиле существующих `TestCase`.

## Безопасность и конфигурация

- Секреты и настройки окружения — только в `config/local_settings.py` (в .gitignore): `SECRET_KEY`, `DATABASES`, `EMAIL_*`, `REPORT_MONTH_EMAIL`. Не коммитить этот файл.
- Если `config/local_settings.py` отсутствует, `config/settings.py` подключает `config/docker_settings.py` — настройки из переменных окружения (режим Docker, образец — `.env.example`, файл `.env` в .gitignore).
- `DEBUG`, `ALLOWED_HOSTS` также задаются в `local_settings.py` (в `settings.py` их нет). `STATIC_URL` и `STATICFILES_DIRS` (корневой `static/`) заданы в `settings.py`, остальные `STATIC_*` — в `local_settings.py`.
- HTTPS-hardening-настройки (`SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS`, `SECURE_CONTENT_TYPE_NOSNIFF`) в `settings.py` не заданы; в шаблоне `config/local_settings.example.py` присутствуют закомментированными — `setup.sh prod` раскомментирует их (при `HTTPS=0` оставляет закомментированными).
- Удаление объектов в `factory`, `newspaper`, `newspaper_numbers` читает id из `request.GET` при DELETE-запросе и не проверяет права — любой авторизованный пользователь может удалить любую запись.
- В `my_distribution` POST-фильтры передаются напрямую в `distributions.get_all()` → `filter(**filter_by)` — при изменениях фильтров ограничивать допустимые ключи.

## Известные проблемы (аудит; не «исправлять» молча, но учитывать)

Номера строк ориентировочные — на момент аудита.

### Критичные (баги, влияющие на работу)

- `press/views.py` (~268, 296, 330, 353) — `HttpResponse(request, '', status='200')` в `towns_delete`, `factory`, `newspaper`, `newspaper_numbers`: request передан первым аргументом вместо контента. Правильно: `HttpResponse('', status=200)`.
- `person/signals.py` — сломан: сигналы подписаны на `django.contrib.auth.models.User`, но используется кастомный `Person` (`AUTH_USER_MODEL`); файл не подключён в `apps.py`. Кандидат на удаление целиком.
- `press/views.py` (~312, 316, view `newspaper`) — `title.strip == ''` без скобок: `.strip` — метод, проверка пустой строки никогда не срабатывает. Нужно `title.strip() == ''`.
- `press/views.py` (~105, `new_distrib`) — риск деления на ноль: `all_quantity // all_memb_count`, когда раздающих 0.
- `person/views.py` (~30-33, profile) — для не-члена партии ищется `Sympathizer` по ФИО; если не найден — `AttributeError` на `.pk`.
- `press/services/report.py` (`_report_month`) — в январе до 4-го числа возвращается декабрь ТОГО ЖЕ года (`replace(month=12)` без уменьшения года), а не прошлого.
- `press/views.py` (~283, view `factory`) — невалидная форма падает с TypeError: `"\n".join(...)` по `ErrorList` вместо строк.
- `press/services/report.py` (~138) — раздача без номеров газет роняет отчёт: `distrib.numbers.all()[0]` → IndexError.

### Высокая важность (безопасность)

- `press/views.py` — DELETE-операции читают id из `request.GET.get('id')`; для деструктивных операций лучше URL-параметры или `request.POST`.
- `config/settings.py` — не заданы `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_CONTENT_TYPE_NOSNIFF` (prod-шаблон `setup.sh` генерирует их в `local_settings.py`, но существующие prod-инстансы, развёрнутые вручную, могли их не задать).
- Существующие prod-инстансы, развёрнутые вручную, могли не задать HTTPS-hardening-настройки (есть в шаблоне `config/local_settings.example.py` и в prod-генерации `setup.sh`).
- `press/services/distributions.py`, `factory.py` — `filter(**filter_by)` принимает произвольный dict из POST; нужен белый список ключей.

### Средняя важность

- `press/views.py` (~266) — `Town.objects.get(pk=pk)` бросает `DoesNotExist` → 500. Использовать `get_object_or_404`.
- `press/views.py` (все delete-view) — нет проверки прав: любой авторизованный пользователь может удалить любой объект.
- `press/models.py` (~87) — `Distribution.count_members()` сломан: `len(self.party_members)` на RelatedManager (нужно `.count()`).
- `press/models.py` (~20) — неочевидный `related_name='newspaper'` на `NewspaperNumber` (логичнее `numbers`).
- `press/views.py` (~287-300) — недостижимый код: `if request.method == 'DELETE'` должен быть `elif` (то же в `newspaper`, `newspaper_numbers`).
- `press/services/report.py` (~41-49) — O(n*m) вложенный цикл сопоставления раздающих; заменить на dict по id.
- `press/views.py` (~39-133) — `new_distrib` ~90 строк с бизнес-логикой; вынести в services.
- `templates/base.html` (~11) — опечатка `meta_descripiton` → `meta_description`.

### Низкая важность / техдолг

- `press/views.py` — DEPRECATED-view всё ещё в коде: `new_party_member_distrib`, `new_sympathizer_distrib`, `hx_delete_party_member`, `hx_add_party_member`.
- `press/services/report.py` (~52-72) — закомментированный блок «OLD REALISATION» (есть в git-истории).
- Опечатки: `err_lsit` → `err_list` (`press/views.py` ~365), `factoryes`/`fabrics` → `factories`, `sypathizer_member_field.html` → `sympathizer_...`, `hx-delete-pary-member` в URL, `autor` → `author` (`press/models.py` ~80, требует миграции).
- `press/models.py` — нет индексов: `Distribution.distribution_date` и FK-поля выиграли бы от них.
- `press/admin.py` (~28-31) — у `DistributionSympathizerMemberAdmin` неверные inlines (должны быть в админке `Distribution`).
- `person/models.py` (~38) — `Person.full_name`: при `last_name`/`first_name = None` получается `"None Иван"`.
- `person/views.py` — нет rate limiting / защиты от брутфорса на логине.
- `press/templates/press/new-distrib.html` (~32) — `max=datenow` только на клиенте; нет серверной валидации даты в будущем.
- `press/views.py` (`towns_delete`) — TODO-комментарий «Слить с предыдущим методом».

## Прочее

- `docs/django_and_database.md` — автогенерируемый файл (указан в .gitignore), не редактировать вручную.
- При изменении структуры, команд или соглашений — обновлять этот файл.
