# Структура репозитория

## В этом комплекте

| Путь | Содержимое |
| --- | --- |
| README.md, AGENTS.md, CONTRIBUTING.md, CHANGE_HISTORY.md | Общее описание, инструкции и процесс |
| spec/product/ | Продукт, сценарии и интерфейс |
| spec/tech/ | Архитектура, данные, RAG, OpenAPI, поток, проверки и будущий CI/CD |
| spec/team.md, spec/plan.md, spec/decisions.md | Роли, задачи и решения |
| docs/ | Ветки, checklist, демонстрация, источники и проверка |
| prototype/ | Реальные файлы автономного mock-интерфейса |
| scripts/check_docs.py | Локальная проверка комплекта |
| .github/workflows/docs-check.yml | Только документационный check на hosted runner |
| .github/pull_request_template.md | Шаблон PR |
| frontend/, backend/, search/, infra/ | README границ будущих реализаций |
| corpus/, benchmark/, tests/ | Форматы и планы; пример benchmark без объявленного gold |

## При реализации

Frontend добавляет React src/Dockerfile/lock; backend — Go cmd/internal/migrations/Dockerfile; RAG — Python app/tests/lock и corpus; DevOps — Compose/Nginx/deployment workflows. Новые файлы соответствуют спецификации и проверяются своим компонентом.

Не создавать папки/файлы без роли только ради «большого проекта». README в пока пустых компонентных каталогах честно показывает текущую границу. Пять runtime-сервисов не означают пять репозиториев: команда использует один monorepo с понятными каталогами.
