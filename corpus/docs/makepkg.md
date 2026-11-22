# makepkg — сборка пакета Arch Linux из PKGBUILD

## Назначение

Сборка локального пакета. Ознакомься с PKGBUILD и исходными файлами, поскольку сборочные инструкции выполняются как код. Родная система для этой команды — Arch Linux. В системных разделах приведены применимые команды.

## Debian

Для пакета Debian используются подготовленные исходники с каталогом debian и dpkg-buildpackage. Сборочные зависимости зависят от проекта.

```bash
dpkg-buildpackage -us -uc -b
```

## Fedora

Для Fedora источники RPM описывают в SPEC. Из доверенного SPEC собирают RPM через rpmbuild.

```bash
sudo dnf install rpm-build
rpmbuild -ba package.spec
```

## Arch Linux

Запускай makepkg от обычного пользователя в каталоге проверенного PKGBUILD. -s запрашивает установку недостающих зависимостей, -i устанавливает собранный пакет.

```bash
sudo pacman -Syu --needed base-devel
makepkg -s
makepkg --packagelist
```

## Источники

- [Debian](https://www.debian.org/doc/manuals/debian-reference/ch02.en.html)
- [Fedora](https://dnf5.readthedocs.io/en/latest/dnf5.8.html)
- [Arch Linux](https://man.archlinux.org/man/makepkg.8.en)
