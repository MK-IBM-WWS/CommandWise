#!/usr/bin/env bash
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$root"

./commandwise.sh up -d --no-build --wait --wait-timeout 120 postgres
./commandwise.sh exec -T postgres sh -s <<'POSTGRES_REPAIR'
set -eu
export LC_ALL=C PGCONNECT_TIMEOUT=5
export PGPASSWORD="${POSTGRES_PASSWORD:?PostgreSQL password is missing from Compose}"
database_query() {
    psql -X -q -w --username=commandwise --dbname=commandwise --port=5432 \
        --set=ON_ERROR_STOP=1 "$@"
}

# The official image can trust loopback connections. Use the same service
# hostname as the backend so the check exercises the network password rule.
if response=$(database_query --host=postgres --command='SELECT 1' 2>&1); then
    exit 0
fi
case "$response" in
    *'password authentication failed for user "commandwise"'*)
        echo "Синхронизируем пароль служебной роли commandwise с конфигурацией Compose."
        ;;
    *)
        printf '%s\n' "$response" >&2
        exit 1
        ;;
esac

# psql hashes the password for the ALTER ROLE operation. Input stays on
# stdin inside this container. The local authentication policy is retained.
if ! response=$(
    printf '%s\n%s\n' "$POSTGRES_PASSWORD" "$POSTGRES_PASSWORD" |
        database_query --host=/var/run/postgresql --command='\password commandwise' 2>&1
); then
    printf '%s\n' "$response" >&2
    echo "Локальное подключение PostgreSQL не разрешило смену пароля. Сверьте пароль роли commandwise с .commandwise/compose.env с помощью вашей учётной записи администратора PostgreSQL." >&2
    exit 1
fi

database_query --host=postgres --command='SELECT 1' >/dev/null
echo "Сетевой вход в PostgreSQL проверен."
POSTGRES_REPAIR
