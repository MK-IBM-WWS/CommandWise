# dpkg-query — владелец файла и список файлов установленного DEB

## Назначение

Проверка, какой пакет установил файл, какие файлы установлены и какова локальная версия. Родная система для этой команды — Debian. В системных разделах приведены применимые команды.

## Debian

dpkg-query -S ищет владельца среди установленных пакетов. -L выводит список файлов конкретного пакета.

```bash
dpkg-query -S /usr/bin/curl
dpkg-query -L curl
dpkg-query -W curl
```

## Fedora

В Fedora аналогичные сведения об установленных пакетах даёт RPM.

```bash
rpm -qf /usr/bin/curl
rpm -ql curl
rpm -q curl
```

## Arch Linux

В Arch соответствующие ключи — -Qo, -Ql и -Q.

```bash
pacman -Qo /usr/bin/curl
pacman -Ql curl
pacman -Q curl
```

## Источники

- [Debian](https://manpages.debian.org/stable/dpkg/dpkg-query.1.en.html)
- [Fedora](https://dnf5.readthedocs.io/en/latest/dnf5.8.html)
- [Arch Linux](https://man.archlinux.org/man/pacman.8.en)
