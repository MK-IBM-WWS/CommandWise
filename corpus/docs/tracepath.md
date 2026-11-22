# tracepath — маршрут и MTU пути

## Назначение

Позволяет посмотреть путь и оценку Path MTU. Обычный режим не требует root.

## Примеры

```bash
tracepath -n example.org
tracepath -4 -n example.org
```

## Особенности

pmtu относится к пути до выбранного узла. Некоторые маршрутизаторы не возвращают диагностические ответы.

## Debian

Если команды нет, установи `iputils-tracepath`. pmtu относится к пути до выбранного узла. Некоторые маршрутизаторы не возвращают диагностические ответы.

```bash
sudo apt install iputils-tracepath
tracepath -n example.org
```

## Fedora

Если команды нет, установи `iputils`. pmtu относится к пути до выбранного узла. Некоторые маршрутизаторы не возвращают диагностические ответы.

```bash
sudo dnf install iputils
tracepath -n example.org
```

## Arch Linux

Если команды нет, установи `iputils`. pmtu относится к пути до выбранного узла. Некоторые маршрутизаторы не возвращают диагностические ответы.

```bash
sudo pacman -Syu iputils
tracepath -n example.org
```

## Источники

- [Debian](https://man7.org/linux/man-pages/man8/tracepath.8.html)
- [Fedora](https://man7.org/linux/man-pages/man8/tracepath.8.html)
- [Arch Linux](https://man7.org/linux/man-pages/man8/tracepath.8.html)
