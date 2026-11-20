#!/usr/bin/env bash
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$root"
if [[ $# != 0 ]]; then
    echo "Использование — ./install-debian.sh" >&2
    exit 2
fi

source /etc/os-release
if [[ "$ID" != debian || "${VERSION_ID:-}" != 13 || "$(dpkg --print-architecture)" != amd64 ]]; then
    echo "Установщик рассчитан на Debian 13 (Trixie), amd64." >&2
    exit 1
fi

if ! command -v nvidia-smi >/dev/null || ! nvidia-smi -L; then
    echo "Установите совместимый драйвер NVIDIA и убедитесь, что nvidia-smi -L видит GPU." >&2
    exit 1
fi

admin_prefix=()
if (( EUID != 0 )); then
    admin_prefix=(sudo)
    sudo -v
fi
as_root() { "${admin_prefix[@]}" "$@"; }
docker_local() { as_root docker --host unix:///var/run/docker.sock "$@"; }

work="$(mktemp -d)"
trap 'rm -rf -- "$work"' EXIT

if [[ ! -s /etc/ssl/certs/ca-certificates.crt ]] || ! command -v curl >/dev/null ||
   ! command -v gpg >/dev/null || ! command -v openssl >/dev/null; then
    as_root apt-get update
    as_root apt-get install -y ca-certificates curl gnupg openssl
fi

if ! docker_local compose version >/dev/null 2>&1 || ! docker_local buildx version >/dev/null 2>&1; then
    if dpkg-query -W -f='${db:Status-Status}\n' podman-docker 2>/dev/null | grep -qx installed; then
        echo "Команду docker предоставляет пакет podman-docker. Для этого установщика нужен Docker Engine." >&2
        exit 1
    fi

    if dpkg-query -W -f='${db:Status-Status}\n' docker.io 2>/dev/null | grep -qx installed; then
        as_root apt-get update
        as_root apt-get install -y --no-remove docker-compose docker-buildx
    else
        if ! grep -qsR 'https://download.docker.com/linux/debian' /etc/apt/sources.list /etc/apt/sources.list.d; then
            as_root install -d -m 0755 /etc/apt/keyrings
            curl --fail --silent --show-error --location --retry 3 \
                https://download.docker.com/linux/debian/gpg -o "$work/docker.asc"
            as_root install -m 0644 "$work/docker.asc" /etc/apt/keyrings/docker.asc
            cat > "$work/docker.sources" <<'APT'
Types: deb
URIs: https://download.docker.com/linux/debian
Suites: trixie
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.asc
APT
            as_root install -m 0644 "$work/docker.sources" /etc/apt/sources.list.d/docker.sources
        fi
        as_root apt-get update
        as_root apt-get install -y --no-remove docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    fi
fi
as_root systemctl enable --now docker

if ! command -v nvidia-ctk >/dev/null; then
    if ! grep -qsR 'nvidia.github.io/libnvidia-container/stable/deb' /etc/apt/sources.list /etc/apt/sources.list.d; then
        curl --fail --silent --show-error --location --retry 3 \
            https://nvidia.github.io/libnvidia-container/gpgkey -o "$work/nvidia.asc"
        gpg --batch --dearmor --output "$work/nvidia.gpg" "$work/nvidia.asc"
        as_root install -m 0644 "$work/nvidia.gpg" /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
        curl --fail --silent --show-error --location --retry 3 \
            https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list -o "$work/nvidia.list"
        sed 's#^deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
            "$work/nvidia.list" > "$work/nvidia-signed.list"
        as_root install -m 0644 "$work/nvidia-signed.list" /etc/apt/sources.list.d/nvidia-container-toolkit.list
    fi
    as_root apt-get update
    as_root apt-get install -y nvidia-container-toolkit
fi

if ! docker_local info --format '{{json .Runtimes}}' | grep -q '"nvidia"'; then
    as_root nvidia-ctk runtime configure --runtime=docker
    as_root systemctl restart docker
fi

bash "$root/infra/install-common.sh"
