#!/usr/bin/env bash
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

# Keep configuration private. Model files remain readable by the containers.
state="$root/.commandwise"
mkdir -p "$state/models/llm" "$state/models/embedding"
chmod 700 "$state"
config="$state/compose.env"
if [[ ! -s "$config" ]]; then
    (
        umask 077
        temporary="$(mktemp "$state/.env-XXXXXX")"
        {
            printf 'POSTGRES_PASSWORD=%s\n' "$(openssl rand -hex 32)"
            printf 'JWT_SECRET=%s\n' "$(openssl rand -hex 48)"
            printf 'CW_BIND=127.0.0.1\nCW_PORT=8080\nCOOKIE_SECURE=false\nPUBLIC_ORIGIN=\n'
        } > "$temporary"
        mv -f -- "$temporary" "$config"
    )
fi

download() {
    local url="$1" dest="$2" sha="$3"
    if [[ -f "$dest" ]] && printf '%s  %s\n' "$sha" "$dest" | sha256sum --check --status; then
        return
    fi
    if [[ ! -f "$dest.part" ]] || ! printf '%s  %s\n' "$sha" "$dest.part" | sha256sum --check --status; then
        echo "Загрузка $(basename -- "$dest")"
        curl --fail --location --retry 3 --connect-timeout 20 --continue-at - --output "$dest.part" "$url"
    fi
    if ! printf '%s  %s\n' "$sha" "$dest.part" | sha256sum --check --status; then
        mv -f -- "$dest.part" "$dest.invalid"
        echo "Контрольная сумма модели не совпала. Запустите установщик ещё раз." >&2
        exit 1
    fi
    chmod 0644 "$dest.part"
    mv -f -- "$dest.part" "$dest"
}
qwen='https://huggingface.co/unsloth/Qwen3.5-4B-GGUF/resolve/e87f176479d0855a907a41277aca2f8ee7a09523'
e5='https://huggingface.co/intfloat/multilingual-e5-small/resolve/614241f622f53c4eeff9890bdc4f31cfecc418b3/onnx'
download "$qwen/Qwen3.5-4B-Q4_K_M.gguf" "$state/models/llm/qwen.gguf" '00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4'
download "$e5/model.onnx" "$state/models/embedding/model.onnx" 'ca456c06b3a9505ddfd9131408916dd79290368331e7d76bb621f1cba6bc8665'
download "$e5/tokenizer.json" "$state/models/embedding/tokenizer.json" '0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39'

./commandwise.sh config --quiet
./commandwise.sh pull postgres llm
./commandwise.sh build backend frontend search
./commandwise.sh up -d --wait --wait-timeout 120 postgres

if [[ ! -f "$state/admin.created" ]]; then
    if [[ ! -t 0 ]]; then
        echo "Запустите установщик из интерактивного терминала, чтобы задать реквизиты администратора." >&2
        exit 1
    fi
    read -r -p 'Логин администратора: ' admin_login
    read -rs -p 'Пароль администратора: ' admin_password
    printf '\n'
    read -rs -p 'Повторите пароль: ' admin_repeat
    printf '\n'
    if [[ "$admin_password" != "$admin_repeat" ]]; then
        echo "Пароли не совпадают." >&2
        exit 1
    fi
    if ! printf '%s\n' "$admin_password" | ./commandwise.sh run --no-deps --rm -T backend admin "$admin_login"; then
        echo "Допустимы латиница, цифры, точка, дефис и подчёркивание в логине. Пароль от 8 символов до 72 байт." >&2
        exit 1
    fi
    unset admin_password admin_repeat
    touch "$state/admin.created"
fi

exec bash "$root/infra/start.sh"
