# Способ проверки

## Первая контрольная точка

1. Выполнить `python3 scripts/check_docs.py`: структура, локальные ссылки, примеры и базовая согласованность.
2. Запустить прототип по README и пройти S01/S03/S04/S05/S06/S07/S09. Проверить ширину ноутбука и около 390 px, copy/source/refresh.
3. Показать настоящие commits/PR команды в GitHub после включения комплекта. История текстового файла CHANGE_HISTORY не заменяет Git.
4. Сохранить фактический вывод проверки и screenshots/результат прохода. Локальные проверки комплекта — [verification](../../docs/verification.md); remote Actions пока не утверждается выполненным.

## Unit и интеграционные проверки — следующие этапы

| Компонент | Существенные проверки |
| --- | --- |
| Go | session ownership, SQL/миграции, idempotency, очередь, timeout, cancel, no_context, snapshots, SSE |
| Frontend React | target из API, история, race смены чата, SSE произвольными блоками UTF-8/JSON, Stop, источники, безопасный Markdown |
| Python | tokenizer flags/case, chunk boundaries, target filter, stable IDs, empty/malformed index, schemas, no-match |
| Интеграция | Реальный запрос Go/BM25/LLM, источник и target, поток через Nginx, refresh, отмена, unavailable dependency |
| Infrastructure | ready, сохранность томов, restore в тестовой БД, rollback image/index, фактическое GPU usage |

CI обычного PR работает без GPU: Go fake clients, Python fixtures, frontend mocks. Полный GPU-benchmark запускается отдельно после принятия кода.

## Benchmark

План: около 60 размеченных вопросов, 40 dev и 20 holdout; объём уточняется по качеству. Формат — [benchmark](../../benchmark/README.md). Подобные вопросы разделяются группами; holdout не подгоняется под ошибки. Gold и reference_answer проверяет человек по исходной документации.

- Recall@5: доля нужных gold-разделов в top-5 по answerable вопросам; при одном gold это доля вопросов с найденным gold.
- Hit@5: есть хотя бы один gold.
- MRR@5: 1/rank первого gold в top-5 либо 0, затем среднее.
- Target violations: несовместимые returned chunks, цель 0.
- Для unanswerable: доля корректных отказов и ложных выдач отдельно от Recall.
- Для ответов: правильность command/flags, оснований, источников и отказов; автоматический поиск слова не заменяет ручную смысловую проверку.
- Время: median/p95 retrieval, time-to-first-token и полное время; cold и warm отдельно.

Предварительная желаемая планка: Recall@5 >=0.8 на answerable holdout и 0 target violations. Это предложенные критерии, не уже достигнутые метрики. Финальный критерий команда согласует до финальной оценки.

Отчёт сохраняет commit, corpus_version, model identity, config, число вопросов, per-question results, ручные оценки и условия запуска. В mock-режиме численные оценки качества RAG не публикуются.
