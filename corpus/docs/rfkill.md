# rfkill — состояние блокировки Wi-Fi и Bluetooth

## Назначение

Различает программную и аппаратную блокировки радиооборудования.

## Примеры

```bash
rfkill list
rfkill list wifi
```

## Особенности

Аппаратную блокировку снимают переключателем устройства или в настройках оборудования. Команда list состояние не меняет.

## Debian

Если команды нет, установи `rfkill`. Аппаратную блокировку снимают переключателем устройства или в настройках оборудования. Команда list состояние не меняет.

```bash
sudo apt install rfkill
rfkill list
```

## Fedora

Если rfkill отсутствует, уточни имя пакета через DNF. В минимальной установке можно найти пакет для утилиты командой dnf provides /usr/sbin/rfkill или dnf provides "*/rfkill".

```bash
dnf provides '*/rfkill'
rfkill list
```

## Arch Linux

Если команды нет, установи `util-linux`. В Arch rfkill входит в набор util-linux. Команда пригодится только на машине с радиоадаптером.

```bash
sudo pacman -Syu util-linux
rfkill list
```

## Источники

- [Debian](https://man7.org/linux/man-pages/man8/rfkill.8.html)
- [Fedora](https://man7.org/linux/man-pages/man8/rfkill.8.html)
- [Arch Linux](https://man7.org/linux/man-pages/man8/rfkill.8.html)
