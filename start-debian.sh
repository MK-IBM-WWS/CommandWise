#!/usr/bin/env bash
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# != 0 ]]; then
    echo "Использование — ./start-debian.sh" >&2
    exit 2
fi
exec bash "$root/infra/start.sh"
