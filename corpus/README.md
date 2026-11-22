# Корпус CommandWise

В `docs/` лежат 50 Markdown-файлов. Во всех есть разделы Debian, Fedora и Arch Linux. Общие приёмы приведены отдельно, источники указаны в конце каждого файла. Пакеты, различия команд и условия работы перечислены в разделах систем. Утилиты конкретного семейства пакетов сопровождаются аналогами для остальных систем.

| Раздел | Команды |
| --- | --- |
| Файлы, процессы и службы (21) | cat, chmod, cp, df, du, find, grep, head, kill, ls, mkdir, mv, ps, rm, sort, ssh, systemctl, tail, tar, uniq, wc |
| Сетевая диагностика (18) | curl, dig, ethtool, host, hostnamectl, ip, mtr, nc, nmcli, nslookup, ping, resolvectl, rfkill, ss, tcpdump, tracepath, traceroute, wget |
| Управление пакетами (11) | apt, apt-cache, apt-file, dnf, dpkg, dpkg-query, flatpak, makepkg, pacman, pactree, rpm |

Примеры по пакетам опираются на [справочник Debian](https://www.debian.org/doc/manuals/debian-reference/ch02.en.html), [документацию DNF5](https://dnf5.readthedocs.io/en/latest/dnf5.8.html) и [справочник pacman](https://man.archlinux.org/man/pacman.8.en). Синтаксис дистрибутива запуска Compose определяется установщиком приложения отдельно от корпуса.

При изменении встроенных материалов манифест получает новый `seed_revision`. Поисковый сервис собирает новый индекс и сохраняет документы из админки. Коллизия с новым именем встроенного документа добавляет пользовательскому документу суффикс `-uploaded-N`. Предыдущие ответы сохраняют сохранённые фрагменты источников.
