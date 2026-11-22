# resolvectl — проверка DNS через systemd-resolved

## Назначение

Показывает DNS-серверы, домены и результаты запросов через systemd-resolved. Для работы сервис должен быть запущен.

## Примеры

```bash
systemctl is-active systemd-resolved
resolvectl status
resolvectl query example.org
```

## Особенности

Если служба не активна, проверь действующий резолвер или выполни запрос через dig. Не меняй /etc/resolv.conf без учёта сетевого менеджера.

## Debian

Утилита входит в `systemd-resolved`. Проверь доступность службы. В Debian установкой systemd-resolved меняется интеграция с системным разрешением имён. Проверь, какой DNS-менеджер активен, перед установкой.

```bash
systemctl is-active systemd-resolved
resolvectl status
```

## Fedora

Утилита входит в `systemd-resolved`. Проверь доступность службы. Если systemd-resolved уже используется, достаточно команды resolvectl status. Наличие сервиса определяет конфигурация машины.

```bash
systemctl is-active systemd-resolved
resolvectl status
```

## Arch Linux

Утилита входит в `systemd`. Активируй systemd-resolved только если он выбран резолвером для этой машины.

```bash
systemctl is-active systemd-resolved
resolvectl status
```

## Источники

- [Debian](https://www.freedesktop.org/software/systemd/man/latest/resolvectl.html)
- [Fedora](https://www.freedesktop.org/software/systemd/man/latest/resolvectl.html)
- [Arch Linux](https://archlinux.org/packages/core/x86_64/systemd/files/)
