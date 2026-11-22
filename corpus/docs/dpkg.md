# dpkg — установка и удаление локальных DEB-пакетов

## Назначение

Низкоуровневое управление установленными DEB-пакетами. Родная система для этой команды — Debian. В системных разделах приведены применимые команды.

## Debian

dpkg -i устанавливает локальный .deb. Если требуются зависимости, сначала оцени список операций в apt install ./package.deb. dpkg -r сохраняет системные конфигурационные файлы пакета.

```bash
dpkg --info ./package.deb
sudo dpkg -i ./package.deb
dpkg -l curl
```

## Fedora

В Fedora .deb не подходит для штатной установки. Посмотри метаданные локального RPM через rpm и устанавливай через DNF с разрешением зависимостей.

```bash
rpm -qip ./package.rpm
sudo dnf install ./package.rpm
```

## Arch Linux

В Arch используй формат pkg.tar.zst и pacman -U. Выбирай сборку для своей архитектуры.

```bash
pacman -Qip ./package.pkg.tar.zst
sudo pacman -U ./package.pkg.tar.zst
```

## Источники

- [Debian](https://manpages.debian.org/stable/dpkg/dpkg.1.en.html)
- [Fedora](https://dnf5.readthedocs.io/en/latest/dnf5.8.html)
- [Arch Linux](https://man.archlinux.org/man/pacman.8.en)
