#!/usr/bin/env bash
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
config="$root/.commandwise/compose.env"

# The deployment file is authoritative for the database credential.
unset POSTGRES_PASSWORD

docker_args=(docker --host unix:///var/run/docker.sock)
if (( EUID != 0 )); then
    docker_args=(sudo "${docker_args[@]}")
fi
compose=("${docker_args[@]}" compose --project-name commandwise \
    --project-directory "$root" -f "$root/infra/compose.yaml")
if [[ -s "$config" ]]; then
    exec "${compose[@]}" --env-file "$config" "$@"
fi
if [[ ${1:-} != down ]]; then
    echo "Сначала выполните ./install-debian.sh на Debian 13." >&2
    exit 1
fi

# Compose still interpolates the service definitions when removing the project.
config="$(mktemp)"
trap 'rm -f -- "$config"' EXIT
printf 'POSTGRES_PASSWORD=unused-for-down\nJWT_SECRET=unused-for-down\n' > "$config"
"${compose[@]}" --env-file "$config" "$@"
