# ethtool — состояние Ethernet и параметры линка

## Назначение

Показывает скорость, дуплекс, состояние линка и сведения о драйвере. Имя интерфейса смотри в ip -br link.

## Примеры

```bash
ethtool enp3s0
ethtool -i enp3s0
sudo ethtool -S enp3s0
```

## Особенности

Поля статистики и возможность чтения зависят от драйвера и типа интерфейса. Примеры читают состояние и счётчики.

## Debian

Если команды нет, установи `ethtool`. Поля статистики и возможность чтения зависят от драйвера и типа интерфейса. Примеры читают состояние и счётчики.

```bash
sudo apt install ethtool
ethtool enp3s0
```

## Fedora

Если команды нет, установи `ethtool`. Поля статистики и возможность чтения зависят от драйвера и типа интерфейса. Примеры читают состояние и счётчики.

```bash
sudo dnf install ethtool
ethtool enp3s0
```

## Arch Linux

Если команды нет, установи `ethtool`. Поля статистики и возможность чтения зависят от драйвера и типа интерфейса. Примеры читают состояние и счётчики.

```bash
sudo pacman -Syu ethtool
ethtool enp3s0
```

## Источники

- [Debian](https://man7.org/linux/man-pages/man8/ethtool.8.html)
- [Fedora](https://man7.org/linux/man-pages/man8/ethtool.8.html)
- [Arch Linux](https://man7.org/linux/man-pages/man8/ethtool.8.html)
