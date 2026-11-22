#!/usr/bin/env bash
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
config="$root/.commandwise/compose.env"
if [[ ! -s "$config" ]]; then
    echo "Сначала выполните ./install-debian.sh на Debian 13 или ./install-fedora.sh на Fedora." >&2
    exit 1
fi

# The deployment file is authoritative for the database credential.
unset POSTGRES_PASSWORD

docker_args=(docker --host unix:///var/run/docker.sock)
if (( EUID != 0 )); then
    docker_args=(sudo "${docker_args[@]}")
fi
exec "${docker_args[@]}" compose --project-name commandwise \
    --project-directory "$root" --env-file "$config" -f "$root/infra/compose.yaml" "$@"
