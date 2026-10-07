# Benchmark

Реальный размеченный набор и результаты ещё не созданы. `questions.example.jsonl` — только пример формата, split=example, без достоверного gold и без использования для метрик.

Рабочий questions.jsonl содержит id, split (dev/holdout), query, distribution, release, answerable, gold\_document\_ids, gold\_sections, reference\_answer, required\_facts и при необходимости history/resolved\_query. Gold подтверждается человеком по реальному корпусу. Числа и критерии — testing.

В отчёте хранить config/versions, per-question выдачу и ответ, метрики, ручные оценки и timings. Example записи не подменяют независимые тестовые вопросы.

