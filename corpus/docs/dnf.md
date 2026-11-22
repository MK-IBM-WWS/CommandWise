# dnf — управление пакетами Fedora

## Назначение

Обновление пакетов Fedora, поиск по репозиториям, установка, удаление, зависимости и локальный RPM. Родная система для этой команды — Fedora. В системных разделах приведены применимые команды.

## Debian

В Debian эти операции выполняет APT. Для поиска файла в репозиториях используй apt-file. Формат локального пакета — .deb.

```bash
sudo apt update
apt search curl
sudo apt install curl
sudo apt upgrade
sudo apt install ./package.deb
```

## Fedora

В Fedora 41 и новее команда dnf обычно вызывает DNF5. Устаревшее имя dnf4 относится к другой реализации. Команды ниже применимы в DNF5. remove перед подтверждением показывает затронутые пакеты.

```bash
dnf search curl
dnf info curl
sudo dnf install curl
sudo dnf upgrade --refresh
dnf provides '*/dig'
sudo dnf remove curl
sudo dnf install ./package.rpm
```

## Arch Linux

В Arch используй pacman. Обновляй базу синхронно с системой, чтобы избежать частичного обновления.

```bash
pacman -Ss curl
sudo pacman -Syu curl
sudo pacman -Syu
sudo pacman -U ./package.pkg.tar.zst
```

## Источники

- [Debian](https://www.debian.org/doc/manuals/debian-reference/ch02.en.html)
- [Fedora](https://dnf5.readthedocs.io/en/latest/dnf5.8.html)
- [Arch Linux](https://man.archlinux.org/man/pacman.8.en)
