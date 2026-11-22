#!/usr/bin/env bash
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

if [[ ! -s .commandwise/compose.env || ! -s .commandwise/models/llm/qwen3-14b.gguf ||
      ! -s .commandwise/models/embedding/model.onnx || ! -s .commandwise/models/embedding/tokenizer.json ]]; then
    echo "Сначала выполните ./install-debian.sh на Debian 13." >&2
    exit 1
fi

# Search runs as an unprivileged user. The bind mount exposes these permissions.
chmod 0755 .commandwise/models/embedding
chmod 0644 .commandwise/models/embedding/{model.onnx,tokenizer.json}

if [[ ${1:-} != --postgres-ready ]]; then
    ./repair-db-auth.sh
fi

if ! ./commandwise.sh up -d --no-build; then
    ./commandwise.sh ps -a >&2 || true
    ./commandwise.sh logs --tail=100 search >&2 || true
    exit 1
fi
url="$(./commandwise.sh port frontend 80)"
url="http://${url/0.0.0.0:/127.0.0.1:}"
printf 'Ожидаем готовности модели и поискового индекса.\n'
for ((attempt=1; attempt<=180; attempt++)); do
    if curl --noproxy '*' --fail --silent --max-time 5 "$url/api/v1/ready" >/dev/null; then
        printf 'CommandWise — %s\nПанель администратора — %s/admin\n' "$url" "$url"
        exit 0
    fi
    sleep 2
done
echo "Сервисы не успели перейти в состояние готовности. Проверьте ./commandwise.sh ps и ./commandwise.sh logs --tail 80" >&2
exit 1
