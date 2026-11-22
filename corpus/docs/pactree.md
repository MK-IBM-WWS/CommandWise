# pactree — дерево зависимостей пакетов Arch Linux

## Назначение

Показывает прямые и обратные зависимости, включая глубину дерева. Родная система для этой команды — Arch Linux. В системных разделах приведены применимые команды.

## Debian

В Debian apt-cache показывает зависимости и пакеты, которые от него зависят.

```bash
apt-cache depends curl
apt-cache rdepends curl
```

## Fedora

В Fedora аналогичный запрос выполняет DNF5 repoquery.

```bash
dnf repoquery --requires curl
dnf repoquery --whatrequires curl
```

## Arch Linux

Установи pacman-contrib. -r показывает обратные зависимости, -d ограничивает глубину. -s использует синхронизированные базы вместо локальной.

```bash
sudo pacman -Syu pacman-contrib
pactree -d 2 curl
pactree -r curl
```

## Источники

- [Debian](https://www.debian.org/doc/manuals/debian-reference/ch02.en.html)
- [Fedora](https://dnf5.readthedocs.io/en/latest/dnf5.8.html)
- [Arch Linux](https://man.archlinux.org/man/pactree.8.en)
