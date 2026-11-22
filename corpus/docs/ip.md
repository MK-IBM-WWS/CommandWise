# ip — адреса, интерфейсы и маршруты

## Назначение

Показывает сетевые интерфейсы, адреса и таблицу маршрутизации. Подставь фактическое имя интерфейса для команды с dev.

## Примеры

```bash
ip -br link
ip -br address
ip route show default
ip route get 192.0.2.1
```

## Особенности

ip route get показывает выбранный маршрут, не отправляя пробный пакет. Временные изменения ip не заменяют постоянный профиль сети.

## Debian

Если команды нет, установи `iproute2`. ip route get показывает выбранный маршрут, не отправляя пробный пакет. Временные изменения ip не заменяют постоянный профиль сети.

```bash
sudo apt install iproute2
ip -br link
```

## Fedora

Если команды нет, установи `iproute`. ip route get показывает выбранный маршрут, не отправляя пробный пакет. Временные изменения ip не заменяют постоянный профиль сети.

```bash
sudo dnf install iproute
ip -br link
```

## Arch Linux

Если команды нет, установи `iproute2`. ip route get показывает выбранный маршрут, не отправляя пробный пакет. Временные изменения ip не заменяют постоянный профиль сети.

```bash
sudo pacman -Syu iproute2
ip -br link
```

## Источники

- [Debian](https://man7.org/linux/man-pages/man8/ip.8.html)
- [Fedora](https://man7.org/linux/man-pages/man8/ip.8.html)
- [Arch Linux](https://man7.org/linux/man-pages/man8/ip.8.html)
