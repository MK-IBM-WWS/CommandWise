# Модель данных рабочей версии

## Статус

Схема проектируется для PostgreSQL; миграции и подключённая база ещё не входят в комплект точки 1. В прототипе используются несвязанные с БД demo-объекты localStorage.

| Таблица | Основные поля | Ограничения |
| --- | --- | --- |
| sessions | id UUID, token_hash TEXT, created_at TIMESTAMPTZ | token_hash уникален; cookie содержит случайный токен, в БД хранится hash |
| chats | id UUID, session_id UUID FK, title TEXT, distribution TEXT, release TEXT, created_at TIMESTAMPTZ | Только владелец сессии; target фиксирован |
| messages | id UUID, chat_id UUID FK, role TEXT, content TEXT, status TEXT, sources JSONB, corpus_version TEXT, finish_reason TEXT, created_at TIMESTAMPTZ | role user/assistant; status complete/generating/cancelled/error |
| requests | chat_id UUID FK, client_request_id UUID, user_message_id UUID FK, assistant_message_id UUID FK, status TEXT | UNIQUE(chat_id, client_request_id) |

## Связи и доступ

Сессия имеет много чатов; чат имеет много сообщений и запросов. Каждая операция с chat_id/message_id проверяет session ownership. Чужой объект отвечает 404 без раскрытия его существования.

Cookie `rag_session`: минимум 32 случайных байта crypto/rand, HttpOnly, SameSite=Lax, Secure на production HTTPS. Очистка cookie в MVP лишает доступа к прежним чатам; восстановление через аккаунт не реализуется.

## Snapshot источников

В assistant message.sources хранится массив полного использованного текста и metadata: ref, chunk_id, document_id, title, command, section, source_url, distribution, release, package_version, corpus_version. Внешний список sources содержит краткие карточки; полный текст выдаётся отдельным маршрутом проверенного сообщения.

После обновления corpus прежний snapshot не пересчитывается. Ссылки модели [n] проверяются по фактическим refs. Недействительная ссылка не получает случайный источник.

## Транзакции и прерывание

Создание request и пары сообщений выполняется атомарно. Не держать транзакцию открытой во время долгого LLM-вызова. При отмене/ошибке частичный assistant content и статус сохраняются. Оставшиеся generating после аварийного restart помечаются interrupted/error.

SQL параметризуется; schema меняется миграциями goose с версией и воспроизводимым запуском. Restore проверяется на отдельной тестовой БД.
