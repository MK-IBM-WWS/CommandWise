# tcpdump — диагностика пакетов на сетевом интерфейсе

## Назначение

Захватывает пакеты на интерфейсе и фильтрует их по протоколу и порту. Используй на интерфейсе, который администрируешь.

## Примеры

```bash
tcpdump -D
sudo tcpdump -ni any -c 20 'udp port 53'
sudo tcpdump -ni enp3s0 -c 20 icmp
```

## Особенности

-n отключает разрешение имён, -c останавливает захват после заданного числа пакетов. Захват обычно требует повышенных прав.

## Debian

Если команды нет, установи `tcpdump`. -n отключает разрешение имён, -c останавливает захват после заданного числа пакетов. Захват обычно требует повышенных прав.

```bash
sudo apt install tcpdump
tcpdump -D
```

## Fedora

Если команды нет, установи `tcpdump`. -n отключает разрешение имён, -c останавливает захват после заданного числа пакетов. Захват обычно требует повышенных прав.

```bash
sudo dnf install tcpdump
tcpdump -D
```

## Arch Linux

Если команды нет, установи `tcpdump`. -n отключает разрешение имён, -c останавливает захват после заданного числа пакетов. Захват обычно требует повышенных прав.

```bash
sudo pacman -Syu tcpdump
tcpdump -D
```

## Источники

- [Debian](https://www.tcpdump.org/manpages/tcpdump.1.html)
- [Fedora](https://www.tcpdump.org/manpages/tcpdump.1.html)
- [Arch Linux](https://www.tcpdump.org/manpages/tcpdump.1.html)
