# apt-file — поиск файла среди пакетов Debian

## Назначение

Находит пакет с нужным файлом, даже если пакет ещё не установлен. Родная система для этой команды — Debian. В системных разделах приведены применимые команды.

## Debian

Установи apt-file и обнови его индексы. Команда search поддерживает обычный поиск и регулярные выражения с -x.

```bash
sudo apt install apt-file
sudo apt-file update
apt-file search -x '/usr/bin/dig$'
apt-file list bind9-dnsutils
```

## Fedora

В Fedora используйте dnf provides с шаблоном полного пути или имени файла.

```bash
dnf provides /usr/bin/dig
dnf provides '*/dig'
```

## Arch Linux

В Arch файл ищут во файловой базе pacman.

```bash
sudo pacman -Fy
pacman -F usr/bin/dig
```

## Источники

- [Debian](https://manpages.debian.org/stable/apt-file/apt-file.1.en.html)
- [Fedora](https://dnf5.readthedocs.io/en/latest/dnf5.8.html)
- [Arch Linux](https://man.archlinux.org/man/pacman.8.en)
