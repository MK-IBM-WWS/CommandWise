#!/usr/bin/env bash
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    printf '%s\n' \
        'Использование — ./uninstall.sh [--purge]' \
        'По умолчанию удаляются контейнеры и сеть CommandWise. Данные и модели сохраняются.' \
        '--purge дополнительно удаляет аккаунты, чаты, опубликованный корпус, настройки, модели и образы сборки.'
}

if (( $# > 1 )); then
    usage >&2
    exit 2
fi

case "${1:-}" in
    "")
        "$root/commandwise.sh" down --remove-orphans
        echo "Контейнеры и сеть CommandWise удалены. Данные, настройки и модели сохранены."
        ;;
    --purge)
        echo "Удаляем контейнеры, данные, настройки и модели CommandWise."
        "$root/commandwise.sh" down --remove-orphans --volumes --rmi local
        rm -rf -- "$root/.commandwise"
        echo "CommandWise и его данные удалены."
        ;;
    -h|--help)
        usage
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac
