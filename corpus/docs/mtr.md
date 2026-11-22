# mtr — повторные измерения задержки по маршруту

## Назначение

Совмещает трассировку маршрута с повторными замерами потерь и задержки.

## Примеры

```bash
mtr -n --report --report-cycles 10 example.org
```

## Особенности

Сопоставляй потери промежуточных узлов с последующими узлами и конечным адресом. Маршрутизатор может ограничивать свои ICMP-ответы.

## Debian

Если команды нет, установи `mtr-tiny`. Сопоставляй потери промежуточных узлов с последующими узлами и конечным адресом. Маршрутизатор может ограничивать свои ICMP-ответы.

```bash
sudo apt install mtr-tiny
mtr -n --report --report-cycles 10 example.org
```

## Fedora

Если команды нет, установи `mtr`. Сопоставляй потери промежуточных узлов с последующими узлами и конечным адресом. Маршрутизатор может ограничивать свои ICMP-ответы.

```bash
sudo dnf install mtr
mtr -n --report --report-cycles 10 example.org
```

## Arch Linux

Если команды нет, установи `mtr`. Сопоставляй потери промежуточных узлов с последующими узлами и конечным адресом. Маршрутизатор может ограничивать свои ICMP-ответы.

```bash
sudo pacman -Syu mtr
mtr -n --report --report-cycles 10 example.org
```

## Источники

- [Debian](https://manpages.debian.org/stable/mtr-tiny/mtr.8.en.html)
- [Fedora](https://manpages.debian.org/stable/mtr-tiny/mtr.8.en.html)
- [Arch Linux](https://manpages.debian.org/stable/mtr-tiny/mtr.8.en.html)
