# pacman — управление пакетами Arch Linux

## Назначение

Установка, полноценное обновление системы, список установленных пакетов и поиск пакетов или файлов в репозиториях. Родная система для этой команды — Arch Linux. В системных разделах приведены применимые команды.

## Debian

В Debian аналог — APT. apt update можно выполнять отдельно, чтобы обновить индексы.

```bash
sudo apt update
apt search curl
sudo apt install curl
sudo apt upgrade
```

## Fedora

В Fedora используй DNF, а для поиска пакета по имени файла — dnf provides.

```bash
dnf search curl
sudo dnf install curl
sudo dnf upgrade --refresh
dnf provides '*/dig'
```

## Arch Linux

Поддерживается полное обновление. Не используй pacman -Sy без полного обновления для установки нового пакета. Для поиска по файлам обнови отдельную файловую базу опцией -Fy.

```bash
pacman -Ss curl
sudo pacman -Syu
sudo pacman -Syu curl
pacman -Qi curl
sudo pacman -Fy
pacman -F usr/bin/dig
sudo pacman -U ./package.pkg.tar.zst
```

## Источники

- [Debian](https://www.debian.org/doc/manuals/debian-reference/ch02.en.html)
- [Fedora](https://dnf5.readthedocs.io/en/latest/dnf5.8.html)
- [Arch Linux](https://man.archlinux.org/man/pacman.8.en)
