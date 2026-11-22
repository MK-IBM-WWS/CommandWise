# head — просмотр начала файла

## Назначение

Команда `head` выводит первые строки или байты файла.

Используется для быстрого просмотра начала логов, таблиц и текстовых документов.

## Синтаксис

```bash
head [параметры] [файл]
```

## Параметры

- `-n N` — вывести первые N строк.
- `-c N` — вывести первые N байтов.
- `-q` — не показывать заголовки файлов.
- `-v` — всегда показывать заголовки файлов.

## Показать первые 10 строк

```bash
head app.log
```

По умолчанию показывает первые десять строк.

## Показать первые 20 строк

```bash
head -n 20 app.log
```

Выводит первые двадцать строк файла.

## Показать первые 100 байтов

```bash
head -c 100 data.txt
```

Выводит первые сто байтов.

## Посмотреть начало нескольких файлов

```bash
head -n 5 first.txt second.txt
```

Показывает первые пять строк каждого файла.

## Debian

Пакет: `coreutils`. -n задаёт число строк с начала файла.

```bash
head -n 20 -- app.log
```

## Fedora

Пакет: `coreutils`. -n задаёт число строк с начала файла.

```bash
head -n 20 -- app.log
```

## Arch Linux

Пакет: `coreutils`. -n задаёт число строк с начала файла.

```bash
head -n 20 -- app.log
```

## Источники

- [Debian](https://manpages.debian.org/stable/coreutils/head.1.en.html)
- [Fedora](https://manpages.debian.org/stable/coreutils/head.1.en.html)
- [Arch Linux](https://manpages.debian.org/stable/coreutils/head.1.en.html)
