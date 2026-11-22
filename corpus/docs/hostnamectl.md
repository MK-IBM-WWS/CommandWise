# hostnamectl — имя узла и свойства системы

## Назначение

Показывает статическое имя, сведения об ОС и виртуализации. Команда работает при доступе к systemd-hostnamed.

## Примеры

```bash
hostnamectl status
hostnamectl --static
```

## Особенности

В chroot и некоторых контейнерах может не быть systemd или D-Bus. В таком случае для чтения имени узла можно использовать hostname.

## Debian

Утилита входит в `systemd`. Проверь доступность службы. В chroot и некоторых контейнерах может не быть systemd или D-Bus. В таком случае для чтения имени узла можно использовать hostname.

```bash
hostnamectl status
```

## Fedora

Утилита входит в `systemd`. Проверь доступность службы. В chroot и некоторых контейнерах может не быть systemd или D-Bus. В таком случае для чтения имени узла можно использовать hostname.

```bash
hostnamectl status
```

## Arch Linux

Утилита входит в `systemd`. Проверь доступность службы. В chroot и некоторых контейнерах может не быть systemd или D-Bus. В таком случае для чтения имени узла можно использовать hostname.

```bash
hostnamectl status
```

## Источники

- [Debian](https://www.freedesktop.org/software/systemd/man/latest/hostnamectl.html)
- [Fedora](https://www.freedesktop.org/software/systemd/man/latest/hostnamectl.html)
- [Arch Linux](https://www.freedesktop.org/software/systemd/man/latest/hostnamectl.html)
