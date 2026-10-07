# Поведение API и поток

OpenAPI-файлы задают схемы целевого API. Реализация будет создана далее. Mocks обязаны использовать те же поля, но текущий автономный прототип не является HTTP mock-сервером и не демонстрирует настоящий SSE транспорт.

## Target и история

Distribution/release валидируются при создании чата по manifest. Чат принадлежит сессии; чужой UUID не раскрывает данные. При POST сообщения target берётся из чата. История выдаётся в хронологическом порядке. UUID client_request_id предотвращает повторную генерацию; 409 REQUEST_EXISTS содержит message_id в error, клиент перечитывает историю.

## JSON и SSE

POST messages с stream=false возвращает JSON CompletedAnswer; stream=true — text/event-stream. Первый event sources даёт assistant message_id и карточки. Дальше token/delta, затем done. event error терминален. До headers — JSON ApiError с HTTP status; после headers — error event. Клиент читает POST fetch, не EventSource.

```text
event: sources
data: {"message_id":"UUID","corpus_version":"VERSION","sources":[]}

event: token
data: {"delta":"Текст ответа"}

event: done
data: {"message_id":"UUID","finish_reason":"no_context"}

```

При Stop отменяется fetch, Go context и upstream; partial ответ сохраняется как cancelled. При случайном EOF без терминального события UI не объявляет успех. Nginx должен отключить buffer и иметь timeout больше разрешённого deadline.

## Коды

| HTTP | code/случай |
| --- | --- |
| 400 | INVALID_REQUEST: JSON/текст/ограничение |
| 404 | NOT_FOUND: несуществующий либо чужой чат/источник |
| 409 | REQUEST_EXISTS или CHAT_BUSY |
| 422 | UNSUPPORTED_TARGET |
| 429 | QUEUE_FULL |
| 503 | SEARCH_UNAVAILABLE, LLM_UNAVAILABLE, NOT_READY |

Отсутствие документа — нормальный результат no_context, а не недоступность сервиса. BM25/API scores не становятся уверенностью модели. Подготовленная модель проверяется ready без полной генерации.
