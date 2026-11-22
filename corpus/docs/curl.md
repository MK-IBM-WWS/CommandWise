# curl — запросы HTTP, заголовки и проверка ответа

## Назначение

Нужен для тестирования HTTP API и получения заголовков. -I отправляет HEAD, -L разрешает переходы по перенаправлениям.

## Примеры

```bash
curl -I --max-time 10 https://example.org/
curl -fLsS --max-time 30 -o example.html https://example.org/
curl -sS -o /dev/null -w '%{http_code}\n' https://example.org/
```

## Особенности

Для диагностики TLS оставляй проверку сертификата включённой. Ответ на HEAD может отличаться от GET.

## Debian

Если команды нет, установи `curl`. Для диагностики TLS оставляй проверку сертификата включённой. Ответ на HEAD может отличаться от GET.

```bash
sudo apt install curl
curl -I --max-time 10 https://example.org/
```

## Fedora

Если команды нет, установи `curl`. Для диагностики TLS оставляй проверку сертификата включённой. Ответ на HEAD может отличаться от GET.

```bash
sudo dnf install curl
curl -I --max-time 10 https://example.org/
```

## Arch Linux

Если команды нет, установи `curl`. Для диагностики TLS оставляй проверку сертификата включённой. Ответ на HEAD может отличаться от GET.

```bash
sudo pacman -Syu curl
curl -I --max-time 10 https://example.org/
```

## Источники

- [Debian](https://curl.se/docs/manpage.html)
- [Fedora](https://curl.se/docs/manpage.html)
- [Arch Linux](https://curl.se/docs/manpage.html)
