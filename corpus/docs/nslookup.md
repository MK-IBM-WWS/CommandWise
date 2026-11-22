# nslookup — DNS-запрос к указанному серверу

## Назначение

Работает интерактивно и как разовая команда. Последним аргументом можно задать DNS-сервер.

## Примеры

```bash
nslookup example.org
nslookup -type=AAAA example.org 1.1.1.1
nslookup -type=MX example.org
```

## Особенности

Сообщение о неавторитетном ответе обычно означает ответ рекурсивного сервера. Это не ошибка.

## Debian

Если команды нет, установи `dnsutils`. Сообщение о неавторитетном ответе обычно означает ответ рекурсивного сервера. Это не ошибка.

```bash
sudo apt install dnsutils
nslookup example.org
```

## Fedora

Если команды нет, установи `bind-utils`. Сообщение о неавторитетном ответе обычно означает ответ рекурсивного сервера. Это не ошибка.

```bash
sudo dnf install bind-utils
nslookup example.org
```

## Arch Linux

Если команды нет, установи `bind`. Сообщение о неавторитетном ответе обычно означает ответ рекурсивного сервера. Это не ошибка.

```bash
sudo pacman -Syu bind
nslookup example.org
```

## Источники

- [Debian](https://bind9.readthedocs.io/en/latest/manpages.html#nslookup-query-internet-name-servers-interactively)
- [Fedora](https://bind9.readthedocs.io/en/latest/manpages.html#nslookup-query-internet-name-servers-interactively)
- [Arch Linux](https://bind9.readthedocs.io/en/latest/manpages.html#nslookup-query-internet-name-servers-interactively)
