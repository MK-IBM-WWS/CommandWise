# rpm — сведения об установленных RPM и их файлах

## Назначение

Низкоуровневая база RPM. Узнать, установлен ли пакет, кто владеет файлом или какие файлы будут входить в пакет. Родная система для этой команды — Fedora. В системных разделах приведены применимые команды.

## Debian

Стандартная база Debian — dpkg. Для файлов и установленной версии используй dpkg-query.

```bash
dpkg-query -S /usr/bin/curl
dpkg-query -L curl
dpkg-query -W curl
dpkg --info ./package.deb
```

## Fedora

rpm -q запрашивает установленный пакет, -qf ищет владельца файла, -qip читает сведения из локального RPM. Для установки с зависимостями используй dnf install.

```bash
rpm -q curl
rpm -qf /usr/bin/curl
rpm -ql curl
rpm -qip ./package.rpm
```

## Arch Linux

Базу установленных пакетов Arch читает pacman.

```bash
pacman -Qo /usr/bin/curl
pacman -Ql curl
pacman -Qip ./package.pkg.tar.zst
```

## Источники

- [Debian](https://www.debian.org/doc/manuals/debian-reference/ch02.en.html)
- [Fedora](https://rpm.org/docs/latest/man/rpm.8)
- [Arch Linux](https://man.archlinux.org/man/pacman.8.en)
