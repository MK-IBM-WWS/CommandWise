# apt-cache — поиск и сведения о пакетах APT

## Назначение

Показывает доступные пакеты, версию-кандидат и зависимости без установки. Родная система для этой команды — Debian. В системных разделах приведены применимые команды.

## Debian

Для актуализации индексов выполни sudo apt update. policy помогает отличить установленную версию от версии-кандидата.

```bash
apt-cache search curl
apt-cache show curl
apt-cache policy curl
apt-cache depends curl
```

## Fedora

У Fedora эквиваленты дают dnf search, dnf info и repoquery.

```bash
dnf search curl
dnf info curl
dnf repoquery --requires curl
```

## Arch Linux

В Arch используй pacman -Ss и -Si для синхронизированных репозиториев, -Qi для установленных пакетов.

```bash
pacman -Ss curl
pacman -Si curl
pacman -Qi curl
```

## Источники

- [Debian](https://manpages.debian.org/stable/apt/apt-cache.8.en.html)
- [Fedora](https://dnf5.readthedocs.io/en/latest/dnf5.8.html)
- [Arch Linux](https://man.archlinux.org/man/pacman.8.en)
