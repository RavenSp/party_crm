#!/usr/bin/env bash
set -euo pipefail

# Скрипт запуска тестов Django на временном PostgreSQL-инстансе.
# Поднимает изолированный postgres в tmp-каталоге (без sudo и без настроенной
# системной БД), прогоняет тесты и останавливает/удаляет инстанс.
# Флаг --coverage запускает измерение покрытия.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

USE_COVERAGE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --coverage)
            USE_COVERAGE=1
            shift
            ;;
        --help|-h)
            cat <<EOF
Использование: $0 [OPTIONS]

Тесты запускаются на временном PostgreSQL-инстансе, который поднимается
автоматически и удаляется после прогона. Системная БД не требуется.

Опции:
  --coverage        Измерить покрытие тестами
  --help, -h        Показать эту справку

Примеры:
  $0                  # тесты на временном PostgreSQL
  $0 --coverage       # тесты + отчёт о покрытии
EOF
            exit 0
            ;;
        *)
            echo "Неизвестный аргумент: $1" >&2
            echo "Запустите $0 --help для справки" >&2
            exit 1
            ;;
    esac
done

if [[ -z "${VIRTUAL_ENV:-}" && -f "venv/bin/activate" ]]; then
    # shellcheck source=/dev/null
    source venv/bin/activate
fi

# Бинарники сервера PostgreSQL (Debian/Ubuntu кладут их в /usr/lib/postgresql/<ver>/bin)
PGBIN=""
if command -v initdb >/dev/null 2>&1; then
    PGBIN="$(dirname "$(command -v initdb)")"
else
    INITDB_PATH="$(find /usr/lib/postgresql -maxdepth 3 -name initdb 2>/dev/null | sort -V | tail -1)"
    if [[ -n "$INITDB_PATH" ]]; then
        PGBIN="$(dirname "$INITDB_PATH")"
    fi
fi
if [[ -z "$PGBIN" ]]; then
    echo "Не найдены бинарники PostgreSQL (initdb). Установите postgresql-server." >&2
    exit 1
fi

DB_USER="$(whoami)"
TMP_DIR="$(mktemp -d /tmp/party_crm_pgtest.XXXXXX)"
TMP_SETTINGS="config/tmp_pgtest_settings.py"

# Свободный порт для временного инстанса
PORT="$(python -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"

cleanup() {
    "$PGBIN/pg_ctl" -D "$TMP_DIR/data" stop -m fast >/dev/null 2>&1 || true
    rm -rf "$TMP_DIR" "$TMP_SETTINGS" config/__pycache__/tmp_pgtest_settings*
}
trap cleanup EXIT

# Поднимаем временный инстанс (fsync off — база одноразовая)
"$PGBIN/initdb" -D "$TMP_DIR/data" -U "$DB_USER" --auth=trust --encoding=UTF-8 --locale=C >/dev/null
"$PGBIN/pg_ctl" -D "$TMP_DIR/data" -l "$TMP_DIR/log" -w \
    -o "-k $TMP_DIR -p $PORT -F" start >/dev/null

# Временный settings-модуль, указывающий на этот инстанс
cat > "$TMP_SETTINGS" <<EOF
"""Автогенерируемый run_tests.sh settings для временного PostgreSQL. Не коммитить."""
from config.settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'party_crm_db',
        'USER': '$DB_USER',
        'HOST': '$TMP_DIR',
        'PORT': '$PORT',
    }
}
EOF

if [[ "$USE_COVERAGE" -eq 1 ]]; then
    coverage run manage.py test --settings=config.tmp_pgtest_settings
    coverage report -m
else
    python manage.py test --settings=config.tmp_pgtest_settings
fi
