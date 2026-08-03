#!/usr/bin/env bash
# Скрипт развёртывания проекта на новой системе (Debian/Ubuntu).
# Выполняет:
#   1. Системные пакеты: python3, python3-venv, git, postgresql.
#   2. База данных PostgreSQL: пользователь и БД для проекта (идемпотентно).
#   3. Виртуальное окружение venv/ и зависимости из requirements.txt.
#   4. config/local_settings.py из шаблона config/local_settings.example.py
#      с подставленными SECRET_KEY и параметрами БД (только если файла нет;
#      в существующем файле синхронизируется пароль БД).
#   5. По запросу — разрешённые команды проекта в config.toml Kimi Code
#      (правила [[permission.rules]], см. «Разрешённые команды» в AGENTS.md).
#
# Использование:
#   ./setup.sh                      # режим разработчика (dev, по умолчанию)
#   ./setup.sh dev                  # то же самое явно
#   ./setup.sh prod                 # развёртывание для запуска CRM (production)
#   SKIP_PACKAGES=1 ./setup.sh      # без установки системных пакетов
#   SKIP_POSTGRES=1 ./setup.sh      # без установки PostgreSQL и создания БД
#   SKIP_VENV=1 ./setup.sh          # без venv и pip install
#   SKIP_MIGRATE=1 ./setup.sh       # без применения миграций (и collectstatic)
#   INSTALL_KIMI_ALLOW=1 ./setup.sh # добавить разрешённые команды без вопроса
#   INSTALL_KIMI_ALLOW=0 ./setup.sh # не добавлять и не спрашивать
#
# Режим prod дополнительно (см. шаг 6):
#   - генерирует config/local_settings.py с DEBUG=False и HTTPS-hardening;
#   - выполняет collectstatic в staticfiles/;
#   - генерирует deploy/gunicorn.conf.py и deploy/party-crm.service
#     (установка systemd-юнита — вручную, команды печатаются в конце).
#
# Параметры режима prod:
#   APP_ALLOWED_HOSTS — домены через запятую для ALLOWED_HOSTS
#                       (напр. "crm.example.com,www.crm.example.com";
#                       если не задано — 'localhost' с TODO)
#   HTTPS=1|0           — включить настройки TLS в local_settings.py
#                         (SECURE_SSL_REDIRECT, secure-куки, HSTS). По умолчанию 1
#
# Параметры БД (используются в local_settings.py и при создании БД):
#   DB_NAME     (по умолчанию party_crm_db)
#   DB_USER     (по умолчанию party_crm)
#   DB_PASSWORD (по умолчанию генерируется случайный)
#   DB_HOST     (по умолчанию localhost)
#   DB_PORT     (по умолчанию 5432)
#
# Прочие пути:
#   KIMI_CODE_HOME — каталог конфигурации Kimi Code (по умолчанию ~/.kimi-code)

set -euo pipefail

cd "$(dirname "$0")"

MODE="${1:-dev}"
case "$MODE" in
    dev|prod) ;;
    *)
        echo "Ошибка: неизвестный режим '$MODE'. Использование: ./setup.sh [dev|prod]" >&2
        exit 1
        ;;
esac

DB_NAME="${DB_NAME:-party_crm_db}"
DB_USER="${DB_USER:-party_crm}"
DB_PASSWORD="${DB_PASSWORD:-}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

if [ "$(id -u)" -eq 0 ]; then
    SUDO=""
else
    SUDO="sudo"
fi

echo "=== Шаг 1. Системные пакеты ==="

if [ "${SKIP_PACKAGES:-0}" = "1" ]; then
    echo "Установка системных пакетов пропущена (SKIP_PACKAGES=1)."
else
    packages=(python3 python3-venv git)
    if [ "${SKIP_POSTGRES:-0}" != "1" ]; then
        packages+=(postgresql)
    fi
    $SUDO apt-get update
    $SUDO apt-get install -y "${packages[@]}"
    echo "Пакеты установлены."
fi

echo "=== Шаг 2. База данных PostgreSQL ==="

if [ "${SKIP_POSTGRES:-0}" = "1" ]; then
    echo "Настройка PostgreSQL пропущена (SKIP_POSTGRES=1)."
    echo "Убедитесь, что БД $DB_NAME существует и доступна пользователю $DB_USER."
else
    if [ -z "$DB_PASSWORD" ]; then
        DB_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
        echo "Пароль БД сгенерирован (записан в config/local_settings.py)."
    fi
    # Идемпотентно: создаём пользователя и БД, только если их ещё нет.
    # Пароль синхронизируем всегда: иначе при уже существующем пользователе
    # он может не совпадать с паролем в config/local_settings.py (шаг 4).
    if ! $SUDO -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -qx 1; then
        $SUDO -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
        echo "Пользователь PostgreSQL $DB_USER создан."
    else
        $SUDO -u postgres psql -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
        echo "Пользователь PostgreSQL $DB_USER уже существует, пароль синхронизирован."
    fi
    if ! $SUDO -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -qx 1; then
        $SUDO -u postgres createdb -O "$DB_USER" "$DB_NAME"
        echo "База данных $DB_NAME создана."
    else
        echo "База данных $DB_NAME уже существует."
    fi
fi

echo "=== Шаг 3. Виртуальное окружение и зависимости ==="

if [ "${SKIP_VENV:-0}" = "1" ]; then
    echo "Создание venv пропущено (SKIP_VENV=1)."
else
    if [ ! -d venv ]; then
        python3 -m venv venv
        echo "Виртуальное окружение создано в venv/."
    else
        echo "Виртуальное окружение venv/ уже существует."
    fi
    ./venv/bin/pip install --quiet --upgrade pip
    ./venv/bin/pip install --quiet -r requirements.txt
    echo "Зависимости из requirements.txt установлены."
fi

echo "=== Шаг 4. config/local_settings.py ==="

if [ -f config/local_settings.py ]; then
    if [ "${SKIP_POSTGRES:-0}" != "1" ] && [ -n "$DB_PASSWORD" ]; then
        # Пароль в файле должен совпадать с паролем, установленным на шаге 2
        sed -i "s/'PASSWORD': '.*'/'PASSWORD': '$DB_PASSWORD'/" config/local_settings.py
        echo "config/local_settings.py уже существует; пароль БД синхронизирован с PostgreSQL."
    else
        echo "config/local_settings.py уже существует, не трогаем."
    fi
else
    SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')"
    cp config/local_settings.example.py config/local_settings.py
    # Подставляем реальные значения в скопированный шаблон.
    # _esc экранирует спецсимволы replacement-строки sed (разделитель — |).
    _esc() { printf '%s' "$1" | sed 's/[&|\\]/\\&/g'; }
    sed -i \
        -e "s|SECRET_KEY = 'your-secret-key-here'|SECRET_KEY = '$(_esc "$SECRET_KEY")'|" \
        -e "s|'NAME': 'party_crm_db'|'NAME': '$(_esc "$DB_NAME")'|" \
        -e "s|'USER': 'your_db_user'|'USER': '$(_esc "$DB_USER")'|" \
        -e "s|'PASSWORD': 'your_db_password'|'PASSWORD': '$(_esc "$DB_PASSWORD")'|" \
        -e "s|'HOST': 'localhost'|'HOST': '$(_esc "$DB_HOST")'|" \
        -e "s|'PORT': '5432'|'PORT': '$(_esc "$DB_PORT")'|" \
        config/local_settings.py
    if [ "$MODE" = "prod" ]; then
        APP_ALLOWED_HOSTS="${APP_ALLOWED_HOSTS:-}"
        if [ -z "$APP_ALLOWED_HOSTS" ]; then
            ALLOWED_HOSTS_PY="'localhost'"
            echo "ПРЕДУПРЕЖДЕНИЕ: APP_ALLOWED_HOSTS не задан, в ALLOWED_HOSTS подставлен 'localhost'."
        else
            ALLOWED_HOSTS_PY="'$(echo "$APP_ALLOWED_HOSTS" | sed "s/ *, */','/g")'"
        fi
        # Включаем продакшен-блок шаблона: DEBUG=False, ALLOWED_HOSTS, STATIC_ROOT
        sed -i \
            -e "s|^DEBUG = True|DEBUG = False|" \
            -e "s|^ALLOWED_HOSTS = .*|ALLOWED_HOSTS = [$(_esc "$ALLOWED_HOSTS_PY")]|" \
            -e "s|^# from pathlib import Path|from pathlib import Path|" \
            -e "s|^# STATIC_ROOT = |STATIC_ROOT = |" \
            config/local_settings.py
        HTTPS="${HTTPS:-1}"
        if [ "$HTTPS" = "1" ]; then
            # Раскомментируем HTTPS-hardening-настройки (при HTTPS=0 остаются закомментированными)
            sed -i "s/^# \(SECURE_SSL_REDIRECT\|SECURE_HSTS_SECONDS\|SESSION_COOKIE_SECURE\|CSRF_COOKIE_SECURE\|SECURE_CONTENT_TYPE_NOSNIFF\) = /\1 = /" config/local_settings.py
        fi
        echo "Создан config/local_settings.py из шаблона (режим prod). Заполните EMAIL_* и проверьте ALLOWED_HOSTS."
    else
        echo "Создан config/local_settings.py из шаблона (режим dev). Заполните настройки почты (EMAIL_*)."
    fi
fi

echo "=== Шаг 5. Миграции ==="

if [ "${SKIP_VENV:-0}" = "1" ] || [ "${SKIP_MIGRATE:-0}" = "1" ]; then
    echo "Миграции пропущены. Выполните вручную: python manage.py migrate"
elif ./venv/bin/python manage.py migrate --check >/dev/null 2>&1; then
    echo "Миграции уже применены."
else
    ./venv/bin/python manage.py migrate
    echo "Миграции применены."
fi

if [ "$MODE" = "prod" ]; then
    echo "=== Шаг 6. Статика и файлы запуска (prod) ==="

    if [ "${SKIP_VENV:-0}" = "1" ] || [ "${SKIP_MIGRATE:-0}" = "1" ]; then
        echo "collectstatic пропущен. Выполните вручную: python manage.py collectstatic --noinput"
    else
        ./venv/bin/python manage.py collectstatic --noinput
        echo "Статика собрана в staticfiles/."
    fi

    PROJECT_DIR="$(pwd)"
    mkdir -p deploy
    cat > deploy/gunicorn.conf.py <<EOF
# Сгенерировано setup.sh (режим prod) $(date +%Y-%m-%d).
bind = '127.0.0.1:8000'
workers = 3
EOF
    cat > deploy/party-crm.service <<EOF
# Установка: см. итоговое сообщение setup.sh
[Unit]
Description=party_crm (gunicorn)
After=network.target

[Service]
User=$(whoami)
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/gunicorn --config $PROJECT_DIR/deploy/gunicorn.conf.py config.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
EOF
    echo "Сгенерированы deploy/gunicorn.conf.py и deploy/party-crm.service."
fi

echo "=== Шаг 7. Разрешённые команды для Kimi Code ==="

# Список разрешённых команд проекта (см. раздел «Разрешённые команды» в AGENTS.md)
# можно добавить в config.toml Kimi Code как правила [[permission.rules]].
install_kimi_allow="${INSTALL_KIMI_ALLOW:-}"
if [ -z "$install_kimi_allow" ]; then
    read -r -p "Добавить разрешённые команды проекта в Kimi Code (config.toml)? [y/N] " answer || answer=""
    case "$answer" in
        [yY]*) install_kimi_allow=1 ;;
        *) install_kimi_allow=0 ;;
    esac
fi

if [ "$install_kimi_allow" != "1" ]; then
    echo "Установка разрешённых команд пропущена."
else
    KIMI_HOME="${KIMI_CODE_HOME:-$HOME/.kimi-code}"
    KIMI_CONFIG="$KIMI_HOME/config.toml"
    MARKER_BEGIN="# party-crm: разрешённые команды (добавлено setup.sh)"
    MARKER_END="# party-crm: конец разрешённых команд"

    # Блок правил между маркерами. При повторном запуске setup.sh блок
    # заменяется целиком, поэтому список правится только здесь (и в AGENTS.md).
    RULES_FILE=$(mktemp)
    cat > "$RULES_FILE" <<EOF
$MARKER_BEGIN
[[permission.rules]]
decision = "allow"
pattern = "Bash(*manage.py check*)"

[[permission.rules]]
decision = "allow"
pattern = "Bash(*manage.py test*)"

[[permission.rules]]
decision = "allow"
pattern = "Bash(*manage.py showmigrations*)"

[[permission.rules]]
decision = "allow"
pattern = "Bash(*manage.py makemigrations*)"

[[permission.rules]]
decision = "allow"
pattern = "Bash(*manage.py runserver*)"

[[permission.rules]]
decision = "allow"
pattern = "Bash(git status*)"

[[permission.rules]]
decision = "allow"
pattern = "Bash(git diff*)"

[[permission.rules]]
decision = "allow"
pattern = "Bash(git log*)"

[[permission.rules]]
decision = "allow"
pattern = "Bash(git show*)"

[[permission.rules]]
decision = "allow"
pattern = "Bash(git branch*)"

[[permission.rules]]
decision = "allow"
pattern = "Bash(which *)"

[[permission.rules]]
decision = "allow"
pattern = "Bash(ls *)"

[[permission.rules]]
decision = "allow"
pattern = "Bash(grep *)"

[[permission.rules]]
decision = "allow"
pattern = "Bash(ps aux*)"
$MARKER_END
EOF

    mkdir -p "$KIMI_HOME"
    if [ ! -f "$KIMI_CONFIG" ]; then
        printf '# %s\n' "$KIMI_CONFIG" > "$KIMI_CONFIG"
    fi

    cp "$KIMI_CONFIG" "$KIMI_CONFIG.$(date +%Y%m%d-%H%M%S).bak"

    if grep -qF "$MARKER_BEGIN" "$KIMI_CONFIG"; then
        # Блок уже установлен: заменяем его между маркерами на актуальную
        # версию. Если старый блок без маркера конца — заменяется до конца файла
        # (ранее блок всегда дописывался в конец config.toml).
        awk -v begin="$MARKER_BEGIN" -v end="$MARKER_END" -v rules="$RULES_FILE" '
            index($0, begin) {
                while ((getline line < rules) > 0) print line
                close(rules)
                skip = 1
                next
            }
            skip {
                if (index($0, end)) skip = 0
                next
            }
            { print }
        ' "$KIMI_CONFIG" > "$KIMI_CONFIG.new"
        mv "$KIMI_CONFIG.new" "$KIMI_CONFIG"
        echo "Правила обновлены в $KIMI_CONFIG (резервная копия рядом, *.bak)."
    else
        { echo; cat "$RULES_FILE"; } >> "$KIMI_CONFIG"
        echo "Правила добавлены в $KIMI_CONFIG (резервная копия рядом, *.bak)."
    fi
    rm -f "$RULES_FILE"

    if command -v kimi >/dev/null; then
        if ! kimi doctor config "$KIMI_CONFIG"; then
            echo "Ошибка: config.toml не прошёл проверку, восстанавливаю резервную копию." >&2
            latest_bak=$(ls -t "$KIMI_CONFIG".*.bak | head -1)
            cp "$latest_bak" "$KIMI_CONFIG"
            exit 1
        fi
    fi
    echo "Применение: /reload в Kimi Code или перезапуск сессии."
fi

echo
echo "Установка завершена (режим $MODE). Следующие шаги:"
echo "  1. Заполните EMAIL_* и REPORT_MONTH_EMAIL в config/local_settings.py"
if [ "$MODE" = "prod" ]; then
    echo "  2. Проверьте ALLOWED_HOSTS и настройки TLS в config/local_settings.py"
    echo "  3. Суперпользователь:  ./venv/bin/python manage.py createsuperuser"
    echo "  4. Установите systemd-юнит (под root):"
    echo "       sudo cp deploy/party-crm.service /etc/systemd/system/"
    echo "       sudo systemctl daemon-reload"
    echo "       sudo systemctl enable --now party-crm"
    echo "  5. Настройте nginx как reverse proxy на 127.0.0.1:8000 (TLS)"
else
    echo "  2. Суперпользователь:  ./venv/bin/python manage.py createsuperuser"
    echo "  3. Сервер разработки:  ./venv/bin/python manage.py runserver"
fi
