# ping — проверка доступности через ICMP

## Назначение

Измеряет ответы ICMP Echo и потери. Проверка по IP помогает отделить проблему маршрута от DNS.

## Примеры

```bash
ping -c 4 1.1.1.1
ping -4 -c 4 example.org
ping -6 -c 4 example.org
```

## Особенности

Отсутствие ответов может означать фильтрацию ICMP. Это не проверка доступности конкретного TCP-сервиса.

## Debian

Если команды нет, установи `iputils-ping`. Отсутствие ответов может означать фильтрацию ICMP. Это не проверка доступности конкретного TCP-сервиса.

```bash
sudo apt install iputils-ping
ping -c 4 1.1.1.1
```

## Fedora

Если команды нет, установи `iputils`. Отсутствие ответов может означать фильтрацию ICMP. Это не проверка доступности конкретного TCP-сервиса.

```bash
sudo dnf install iputils
ping -c 4 1.1.1.1
```

## Arch Linux

Если команды нет, установи `iputils`. Отсутствие ответов может означать фильтрацию ICMP. Это не проверка доступности конкретного TCP-сервиса.

```bash
sudo pacman -Syu iputils
ping -c 4 1.1.1.1
```

## Источники

- [Debian](https://man7.org/linux/man-pages/man8/ping.8.html)
- [Fedora](https://man7.org/linux/man-pages/man8/ping.8.html)
- [Arch Linux](https://man7.org/linux/man-pages/man8/ping.8.html)
