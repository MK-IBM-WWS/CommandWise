# dig — подробные DNS-запросы

## Назначение

Показывает ответ DNS, тип записи, статус и использованный сервер.

## Примеры

```bash
dig example.org A
dig example.org AAAA +short
dig @1.1.1.1 example.org MX
```

## Особенности

Подробный вывод помогает различать NXDOMAIN, SERVFAIL и пустой ответ. При прямом обращении к серверу можно обойти локальный кэш и конфигурацию резолвера.

## Debian

Если команды нет, установи `dnsutils`. Подробный вывод помогает различать NXDOMAIN, SERVFAIL и пустой ответ. При прямом обращении к серверу можно обойти локальный кэш и конфигурацию резолвера.

```bash
sudo apt install dnsutils
dig example.org A
```

## Fedora

Если команды нет, установи `bind-utils`. Подробный вывод помогает различать NXDOMAIN, SERVFAIL и пустой ответ. При прямом обращении к серверу можно обойти локальный кэш и конфигурацию резолвера.

```bash
sudo dnf install bind-utils
dig example.org A
```

## Arch Linux

Если команды нет, установи `bind`. Подробный вывод помогает различать NXDOMAIN, SERVFAIL и пустой ответ. При прямом обращении к серверу можно обойти локальный кэш и конфигурацию резолвера.

```bash
sudo pacman -Syu bind
dig example.org A
```

## Источники

- [Debian](https://bind9.readthedocs.io/en/latest/manpages.html#dig-dns-lookup-utility)
- [Fedora](https://bind9.readthedocs.io/en/latest/manpages.html#dig-dns-lookup-utility)
- [Arch Linux](https://bind9.readthedocs.io/en/latest/manpages.html#dig-dns-lookup-utility)
