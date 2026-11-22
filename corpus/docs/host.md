# host — быстрый запрос DNS и обратное разрешение

## Назначение

Показывает DNS-записи в кратком виде. Для IP-адреса делает обратный запрос PTR.

## Примеры

```bash
host example.org
host -t MX example.org
host 1.1.1.1
```

## Особенности

Результат PTR может отличаться от исходного имени. Если нужен подробный DNS-ответ со статусом и TTL, используй dig.

## Debian

Если команды нет, установи `bind9-host`. Результат PTR может отличаться от исходного имени. Если нужен подробный DNS-ответ со статусом и TTL, используй dig.

```bash
sudo apt install bind9-host
host example.org
```

## Fedora

Если команды нет, установи `bind-utils`. Результат PTR может отличаться от исходного имени. Если нужен подробный DNS-ответ со статусом и TTL, используй dig.

```bash
sudo dnf install bind-utils
host example.org
```

## Arch Linux

Если команды нет, установи `bind`. Результат PTR может отличаться от исходного имени. Если нужен подробный DNS-ответ со статусом и TTL, используй dig.

```bash
sudo pacman -Syu bind
host example.org
```

## Источники

- [Debian](https://bind9.readthedocs.io/en/latest/manpages.html#host-dns-lookup-utility)
- [Fedora](https://bind9.readthedocs.io/en/latest/manpages.html#host-dns-lookup-utility)
- [Arch Linux](https://bind9.readthedocs.io/en/latest/manpages.html#host-dns-lookup-utility)
