# GitHub и план CI/CD

## Точка 1: только проверка комплекта

Workflow `.github/workflows/docs-check.yml` запускает `scripts/check_docs.py` на GitHub-hosted Ubuntu для push в main и Pull Requests. Права — contents:read, production-секреты и кафедральный runner не используются. Он не устанавливает Go/модель, не разворачивает сервер и не подтверждает benchmark.

До загрузки и реального успешного run нельзя отмечать Actions как настроенный/прошедший. Hosted-runs зависят от включённых Actions, тарифных квот и доступа репозитория.

## Целевая доставка

После реализации сервисов:

1. PR: документация/контракты, Go tests, frontend typecheck/build, Python tests и retrieval dev-benchmark на изолированных runners без GPU.
2. Принятая main: сборка трёх собственных images, commit SHA tags, публикация в GHCR.
3. Явный запуск deployment workflow для main: доверенный self-hosted runner кафедрального сервера получает задания исходящими соединениями к GitHub; публичный входящий IP не требуется.
4. Миграции, новый image/index, ready и smoke; сохранив данные и предыдущий release.
5. Полный GPU-benchmark отдельной задачей, последовательно.

Все перечисленные steps — план; deploy workflow пока не включён в комплект. GHCR имена вида `ghcr.io/owner/linux-rag-backend:<sha>` уточняются после выбора реального owner/repo. Authentication в Actions и долговечное право pull сервера проектируются отдельно; не хранить PAT в workflow или браузере.

## Границы self-hosted

Production runner выполняет только доверенную принятую версию. Не направлять PR/fork code на основной сервер, не использовать pull_request_target для checkout и исполнения произвольного кода. Labels/runs-on сами по себе не являются авторизацией; доступ runner, triggers, проверка ref и минимальные права должны действовать вместе.

Статус и настройки protection/environments зависят от GitHub-тарифа; при недоступных механизмах для этапа реализации выбирается ручной ограниченный deployment, а не фиктивная «защита». Для точки 1 self-hosted runner не нужен.

## Проверка

Новый commit проходит проверки; release-info включает images, corpus_version и model config; ready/smoke подтверждены; rollback учитывает совместимость БД; backup восстановлен в отдельной среде.

Источники: GitHub Actions self-hosted runners и Container Registry — [список источников](../../docs/sources.md).
