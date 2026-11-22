# ss — сокеты и прослушиваемые порты

## Назначение

Используется для просмотра TCP и UDP, локальных портов и активных соединений.

## Примеры

```bash
ss -lnt
ss -lnu
ss -lnt 'sport = :8080'
sudo ss -lntp
```

## Особенности

-l показывает слушающие сокеты, -n отключает разрешение имён, -p показывает процессы при достаточных правах.

## Debian

Если команды нет, установи `iproute2`. -l показывает слушающие сокеты, -n отключает разрешение имён, -p показывает процессы при достаточных правах.

```bash
sudo apt install iproute2
ss -lnt
```

## Fedora

Если команды нет, установи `iproute`. -l показывает слушающие сокеты, -n отключает разрешение имён, -p показывает процессы при достаточных правах.

```bash
sudo dnf install iproute
ss -lnt
```

## Arch Linux

Если команды нет, установи `iproute2`. -l показывает слушающие сокеты, -n отключает разрешение имён, -p показывает процессы при достаточных правах.

```bash
sudo pacman -Syu iproute2
ss -lnt
```

## Источники

- [Debian](https://man7.org/linux/man-pages/man8/ss.8.html)
- [Fedora](https://man7.org/linux/man-pages/man8/ss.8.html)
- [Arch Linux](https://man7.org/linux/man-pages/man8/ss.8.html)
