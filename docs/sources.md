# Источники требований и решений

## Требования курса

Приложенная презентация «Занятие_1_О_курсе_и_SDD_v5.pdf», НИРС 2026, МГТУ им. Н. Э. Баумана:

- Слайд 4: три зоны ответственности, понимание общего пути и запуска.
- Слайды 5–6: BM25/LLM, собственный benchmark, код/документы/проверки согласованы.
- Слайды 9–11: спецификация поведения и проверки до кода; структура файлов допускает изменения.
- Слайд 12: состав первой точки; работающий RAG пока не требуется.

Презентация не навязывает Go, React, FastAPI, Docker, GitHub, Tailscale, конкретную модель, названия веток, число файлов или объём benchmark. Это решения данной команды.

## Первичные технические материалы

- GitHub Flow: https://docs.github.com/en/get-started/using-github/github-flow
- Защита веток: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- Self-hosted Actions: https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners
- GHCR: https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry
- Checkout action: https://github.com/actions/checkout
- Tailscale: https://tailscale.com/docs/reference/connection-types
- Go: https://pkg.go.dev/net/http
- FastAPI: https://fastapi.tiangolo.com/tutorial/
- rank-bm25: https://github.com/dorianbrown/rank_bm25
- React/Vite: https://react.dev/learn и https://vite.dev/guide/
- Ollama GPU/API: https://docs.ollama.com/gpu и https://docs.ollama.com/api/openai-compatibility
- Qwen GGUF: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF

## Источники будущего corpus

GNU coreutils/findutils/grep/tar, OpenSSH и man-страницы действительных пакетов выбранных окружений. Точный перечень, версии, даты, лицензии и привязки к chunks появятся при сборе corpus. Примерные ссылки prototype не заменяют каталог источников полного корпуса.
