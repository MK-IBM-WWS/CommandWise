# Go API

Запуск рабочей сборки описан в [главном README](../README.md). Backend использует `net/http`, PostgreSQL и goose. Основные параметры окружения — `DATABASE_URL`, `JWT_SECRET`, `SEARCH_URL`, `LLM_URL`, `LLM_MODEL`, `LISTEN_ADDR`, `COOKIE_SECURE`, `PUBLIC_ORIGIN`.

Схемы внешнего API и очереди находятся в [технической спецификации](../spec/tech/api.yaml). Интеграционный тест требует переменную `COMMANDWISE_TEST_DSN` с адресом отдельной пустой базы.
