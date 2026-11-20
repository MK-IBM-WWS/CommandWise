#!/usr/bin/env bash
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$root"
if [[ $# != 0 ]]; then
    echo "Использование: ./install-fedora.sh" >&2
    exit 2
fi

source /etc/os-release
if [[ "$ID" != fedora || "$(uname -m)" != x86_64 ]]; then
    echo "Установщик рассчитан на Fedora Linux x86_64." >&2
    exit 1
fi

if ! command -v nvidia-smi >/dev/null || ! nvidia-smi -L; then
    echo "Установите драйвер NVIDIA для Fedora. После перезагрузки nvidia-smi должен видеть RTX 4070." >&2
    echo "Инструкция: https://rpmfusion.org/Howto/NVIDIA" >&2
    exit 1
fi

admin_prefix=()
if (( EUID != 0 )); then
    admin_prefix=(sudo)
    sudo -v
fi
as_root() { "${admin_prefix[@]}" "$@"; }
docker_local() { as_root docker --host unix:///var/run/docker.sock "$@"; }

if ! command -v docker >/dev/null || ! docker_local compose version >/dev/null 2>&1; then
    if rpm -q podman-docker >/dev/null 2>&1; then
        echo "Пакет podman-docker предоставляет команду docker. Удалите пакет совместимости: sudo dnf remove podman-docker" >&2
        exit 1
    fi
    as_root dnf -y install dnf-plugins-core curl openssl
    if [[ ! -f /etc/yum.repos.d/docker-ce.repo ]]; then
        as_root dnf config-manager addrepo --from-repofile https://download.docker.com/linux/fedora/docker-ce.repo
    fi
    as_root dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
else
    if ! command -v curl >/dev/null || ! command -v openssl >/dev/null; then
        as_root dnf -y install curl openssl
    fi
fi
as_root systemctl enable --now docker

if ! command -v nvidia-ctk >/dev/null; then
    repo="$(mktemp)"
    trap 'rm -f -- "$repo"' EXIT
    curl --fail --silent --show-error --location --retry 3 \
        https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo -o "$repo"
    as_root install -m 0644 "$repo" /etc/yum.repos.d/nvidia-container-toolkit.repo
    as_root dnf -y install nvidia-container-toolkit
fi
if ! docker_local info --format '{{json .Runtimes}}' | grep -q '"nvidia"'; then
    as_root nvidia-ctk runtime configure --runtime=docker
    as_root systemctl restart docker
fi

exec bash "$root/infra/install-common.sh"
