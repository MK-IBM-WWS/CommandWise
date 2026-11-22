# nmcli — состояние сети и профили NetworkManager

## Назначение

Работает на машинах, сетью которых управляет активная служба NetworkManager. Показывает устройства, профили и параметры.

## Примеры

```bash
nmcli device status
nmcli connection show --active
nmcli device show
```

## Особенности

Если устройство отмечено unmanaged, его может обслуживать другой сетевой менеджер. Установка пакета сама по себе не переносит управление сетью.

## Debian

Если команды нет, установи `network-manager`. На сервере сеть может обслуживать ifupdown или systemd-networkd. nmcli применяется только к интерфейсам NetworkManager.

```bash
sudo apt install network-manager
nmcli device status
```

## Fedora

Если команды нет, установи `NetworkManager`. Для управляемых интерфейсов Fedora обычно использует профили NetworkManager. Проверяй реально активные профили на хосте.

```bash
sudo dnf install NetworkManager
nmcli device status
```

## Arch Linux

Если команды нет, установи `networkmanager`. Устанавливай NetworkManager, только если он выбран сетевым менеджером. Не запускай одновременно несколько служб управления одним интерфейсом.

```bash
sudo pacman -Syu networkmanager
nmcli device status
```

## Источники

- [Debian](https://networkmanager.dev/docs/api/latest/nmcli.html)
- [Fedora](https://networkmanager.dev/docs/api/latest/nmcli.html)
- [Arch Linux](https://networkmanager.dev/docs/api/latest/nmcli.html)
