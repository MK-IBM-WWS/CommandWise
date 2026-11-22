# nc — проверка TCP-соединения с сервисом

## Назначение

Подключается к указанному узлу и порту. Пример проверяет только установление TCP-соединения, прикладной протокол проверяют отдельно.

## Примеры

```bash
nc -vz -w 3 example.org 443
```

## Особенности

Реализации OpenBSD nc и Ncat различаются дополнительными ключами. Базовые ключи проверки из примера подходят обеим.

## Debian

Если команды нет, установи `netcat-openbsd`. Реализации OpenBSD nc и Ncat различаются дополнительными ключами. Базовые ключи проверки из примера подходят обеим.

```bash
sudo apt install netcat-openbsd
nc -vz -w 3 example.org 443
```

## Fedora

Если команды нет, установи `nmap-ncat`. Пакет nmap-ncat предоставляет Ncat. Если /usr/bin/nc отсутствует в конкретной сборке, тот же пример можно выполнить с ncat.

```bash
sudo dnf install nmap-ncat
nc -vz -w 3 example.org 443
```

## Arch Linux

Если команды нет, установи `openbsd-netcat`. Реализации OpenBSD nc и Ncat различаются дополнительными ключами. Базовые ключи проверки из примера подходят обеим.

```bash
sudo pacman -Syu openbsd-netcat
nc -vz -w 3 example.org 443
```

## Источники

- [Debian](https://man.openbsd.org/nc.1)
- [Fedora](https://nmap.org/book/ncat-man.html)
- [Arch Linux](https://man.archlinux.org/man/nc.1.en)
