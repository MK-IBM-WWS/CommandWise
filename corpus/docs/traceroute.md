# traceroute — просмотр промежуточных узлов маршрута

## Назначение

Показывает узлы, отвечающие на пробы с увеличивающимся TTL. По умолчанию обычный Linux traceroute применяет UDP.

## Примеры

```bash
traceroute -n -m 15 example.org
traceroute -4 -n example.org
```

## Особенности

Звёздочки означают, что на отдельную пробу нет ответа. Наличие звёздочек не доказывает обрыв на этом узле.

## Debian

Если команды нет, установи `traceroute`. Звёздочки означают, что на отдельную пробу нет ответа. Наличие звёздочек не доказывает обрыв на этом узле.

```bash
sudo apt install traceroute
traceroute -n -m 15 example.org
```

## Fedora

Если команды нет, установи `traceroute`. Звёздочки означают, что на отдельную пробу нет ответа. Наличие звёздочек не доказывает обрыв на этом узле.

```bash
sudo dnf install traceroute
traceroute -n -m 15 example.org
```

## Arch Linux

Если команды нет, установи `traceroute`. Звёздочки означают, что на отдельную пробу нет ответа. Наличие звёздочек не доказывает обрыв на этом узле.

```bash
sudo pacman -Syu traceroute
traceroute -n -m 15 example.org
```

## Источники

- [Debian](https://man7.org/linux/man-pages/man8/traceroute.8.html)
- [Fedora](https://man7.org/linux/man-pages/man8/traceroute.8.html)
- [Arch Linux](https://man7.org/linux/man-pages/man8/traceroute.8.html)
