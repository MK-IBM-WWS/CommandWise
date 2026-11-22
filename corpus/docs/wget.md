# wget — скачивание файлов по HTTP и HTTPS

## Назначение

Скачивает файлы в текущий каталог или по пути, указанному через -O. -c может продолжить прерванную загрузку, если сервер поддерживает диапазоны.

## Примеры

```bash
wget --spider https://example.org/
wget -O example.html https://example.org/
```

## Особенности

При -O имеющийся файл может быть перезаписан. Указывай имя под результат явно.

## Debian

Если команды нет, установи `wget`. При -O имеющийся файл может быть перезаписан. Указывай имя под результат явно.

```bash
sudo apt install wget
wget --spider https://example.org/
```

## Fedora

Проверь, какой пакет предоставляет команду. Если команды нет, можно установить совместимый CLI из wget2-wget. В современных Fedora команду wget может предоставлять wget2-wget. Для варианта из пакета wget проверь реализацию командой wget --version.

```bash
command -v wget
sudo dnf install wget2-wget
wget --spider https://example.org/
```

## Arch Linux

Если команды нет, установи `wget`. При -O имеющийся файл может быть перезаписан. Указывай имя под результат явно.

```bash
sudo pacman -Syu wget
wget --spider https://example.org/
```

## Источники

- [Debian](https://manpages.debian.org/stable/wget/wget.1.en.html)
- [Fedora](https://packages.fedoraproject.org/pkgs/wget2/wget2-wget/)
- [Arch Linux](https://manpages.debian.org/stable/wget/wget.1.en.html)
