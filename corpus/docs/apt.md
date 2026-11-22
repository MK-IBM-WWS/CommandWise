# apt — управление пакетами Debian

## Назначение

Обновление списка репозиториев, поиск пакетов, установка, удаление и обновление системы. Установка локального .deb через APT подтягивает доступные зависимости. Родная система для этой команды — Debian. В системных разделах приведены применимые команды.

## Debian

Используй APT для пакетов Debian. apt update обновляет индексы, apt upgrade обновляет установленные пакеты. apt remove удаляет пакет, apt purge удаляет также его системные конфигурационные файлы. Для сценариев автоматизации предпочтительны apt-get и apt-cache.

```bash
sudo apt update
apt search curl
sudo apt install curl
sudo apt upgrade
sudo apt install ./package.deb
```

## Fedora

В Fedora аналогичные операции выполняет DNF. Формат локальных пакетов — RPM. См. раздел dnf.

```bash
dnf search curl
sudo dnf install curl
sudo dnf upgrade --refresh
sudo dnf install ./package.rpm
```

## Arch Linux

В Arch менеджер пакетов — pacman. При синхронизации базы одновременно обновляй систему. Для локального пакета используй архив формата pkg.tar.zst.

```bash
pacman -Ss curl
sudo pacman -Syu curl
sudo pacman -Syu
sudo pacman -U ./package.pkg.tar.zst
```

## Источники

- [Debian](https://manpages.debian.org/stable/apt/apt.8.en.html)
- [Fedora](https://dnf5.readthedocs.io/en/latest/dnf5.8.html)
- [Arch Linux](https://man.archlinux.org/man/pacman.8.en)
