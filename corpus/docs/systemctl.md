# systemctl — состояние служб и управление systemd

## Назначение

status и is-active читают состояние, enable задаёт запуск при старте, --now сразу запускает службу вместе с enable. Операции управления системными службами обычно требуют root.

## Debian

Сервер OpenSSH поставляется пакетом openssh-server, штатное имя службы — ssh.service. Команды ниже показывают состояние.

```bash
systemctl status ssh.service
systemctl list-unit-files --type=service
```

## Fedora

Сервер OpenSSH поставляется пакетом openssh-server и использует sshd.service. Для NetworkManager действует NetworkManager.service.

```bash
systemctl status sshd.service
systemctl is-active NetworkManager.service
```

## Arch Linux

Пакет openssh включает сервер и клиент. Состояние сервера смотри у sshd.service. В среде без работающего systemd вызов может завершиться ошибкой.

```bash
systemctl status sshd.service
systemctl list-units --type=service
```

## Источники

- [Debian](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html)
- [Fedora](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html)
- [Arch Linux](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html)
