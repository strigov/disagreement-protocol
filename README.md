# Disagreement Protocol

Локальный инструмент для генерации протокола разногласий из `.docx`-договора с правками Word Track Changes.

Приложение состоит из:

- `backend/` - FastAPI, Celery, PostgreSQL, Redis, MinIO/S3, OOXML-пайплайн и экспорт DOCX.
- `frontend/` - Next.js UI для загрузки документа, проверки сторон, редактирования таблицы и экспорта.
- `docker-compose.yml` - локальные сервисы: PostgreSQL, Redis, MinIO.

## Требования

- Python 3.12. Рекомендуется именно 3.12: тесты и зависимости проекта рассчитаны на эту ветку.
- `uv` для Python-зависимостей.
- Node.js 20+ и npm.
- Docker Desktop или совместимый Docker Compose.

Входной файл должен быть `.docx` без макросов, желательно с правками в режиме рецензирования. `.doc` не поддерживается. Максимальный размер загрузки - 25 MB.

## Быстрый запуск

### Автоматически

Из корня проекта:

```bash
./scripts/install.sh
./scripts/start.sh
```

`install.sh` поднимает Docker-сервисы, ставит backend-зависимости на Python 3.12, применяет миграции и устанавливает frontend-зависимости. `start.sh` запускает FastAPI, Celery worker и Next.js в одном терминале.

Откройте `http://localhost:3000`. Для остановки приложения нажмите `Ctrl+C` в терминале со `start.sh`. Docker-контейнеры при этом останутся запущенными; остановить их можно командой:

```bash
docker compose down
```

Полезные опции:

```bash
./scripts/install.sh --skip-frontend
./scripts/install.sh --skip-docker
./scripts/start.sh --skip-migrations
./scripts/start.sh --skip-docker
```

### Вручную

#### 1. Поднять инфраструктуру

Из корня проекта:

```bash
docker compose up -d
```

Будут доступны:

- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- MinIO S3 API: `localhost:9000`
- MinIO Console: `http://localhost:9001`

Локальные значения по умолчанию уже зашиты в backend и совпадают с `.env.example`. Если нужно переопределить настройки, запускайте backend из папки `backend/` и создайте там файл `.env`.

#### 2. Установить backend и применить миграции

В отдельном терминале:

```bash
cd backend
uv sync --python 3.12 --extra dev
uv run alembic upgrade head
```

#### 3. Запустить FastAPI

В отдельном терминале:

```bash
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Проверка:

```bash
curl http://localhost:8000/health
```

Ожидаемый ответ:

```json
{"status":"ok"}
```

#### 4. Запустить Celery worker

В отдельном терминале:

```bash
cd backend
uv run celery -A app.workers.celery_app:celery_app worker --loglevel=info --pool=solo
```

Worker нужен, чтобы после загрузки `.docx` документ реально разобрался: backend кладёт задачу в Redis, а Celery выполняет OOXML-пайплайн.

#### 5. Запустить frontend

В отдельном терминале:

```bash
cd frontend
npm install
npm run dev
```

Откройте `http://localhost:3000`.

Frontend обращается к `/api/*`; Next.js проксирует эти запросы на `http://localhost:8000/api/*`.

## Как пользоваться

1. Откройте `http://localhost:3000`.
2. Перетащите `.docx` с Track Changes в область загрузки или выберите файл через кнопку.
3. Дождитесь экрана предварительного отчёта. На нём отображаются количество правок, format-only правки, статистика нумерации и диагностика.
4. Перейдите дальше и проверьте две стороны договора.
5. Укажите drafting party - сторону, от чьего имени составляется протокол.
6. Нажмите `Построить протокол`.
7. На экране таблицы проверьте строки протокола:
   - редактируйте текст в колонках;
   - добавляйте строки;
   - удаляйте лишние строки;
   - объединяйте соседние строки;
   - при необходимости меняйте drafting party через swap.
8. Нажмите `Экспорт DOCX`.
9. Укажите имя файла и сохраните итоговый протокол.

Итоговый документ экспортируется как `.docx` с таблицей протокола разногласий.

## Как лучше проверить работу

### Минимальная автоматическая проверка

Backend:

```bash
cd backend
uv run python --version
uv run pytest
```

Версия Python должна быть `3.12.x`. Если `uv` использует другое уже созданное окружение, пересоздайте backend-окружение на Python 3.12 и повторите `uv sync --python 3.12 --extra dev`.

Frontend:

```bash
cd frontend
npm test
```

Production-сборка frontend:

```bash
cd frontend
npm run build
```

### Рекомендуемая ручная проверка

Лучше всего проверять приложение на реальном `.docx`, созданном в Word или LibreOffice:

1. Создайте небольшой договор на русском языке.
2. Включите Track Changes / режим рецензирования.
3. Сделайте несколько разных правок:
   - вставка текста внутри пункта;
   - удаление текста;
   - добавление нового пункта;
   - удаление пункта целиком;
   - правка в пункте с нумерацией `1.1`, `1.2` и т.п.
4. Загрузите файл в UI.
5. Проверьте, что статус доходит до предварительного отчёта, а не остаётся на анализе.
6. Проверьте, что стороны извлечены или могут быть исправлены вручную.
7. Постройте протокол и сравните строки таблицы с исходными правками в Word.
8. Отредактируйте одну строку, добавьте одну строку и удалите одну строку.
9. Экспортируйте DOCX.
10. Откройте экспортированный файл и убедитесь, что:
    - есть таблица с 4 колонками;
    - номера пунктов соответствуют исходному договору;
    - исходная и предлагаемая редакции попали в правильные колонки;
    - ручные правки из UI сохранились;
    - имя файла корректное и заканчивается на `.docx`.

### Быстрая API-проверка

Когда backend запущен:

```bash
curl http://localhost:8000/health
```

Загрузка документа через API:

```bash
curl -F "file=@/absolute/path/to/contract.docx" \
  http://localhost:8000/api/documents
```

Ответ содержит `id`. По нему можно смотреть анализ:

```bash
curl http://localhost:8000/api/documents/<document-id>/analysis
```

Если `status` стал `parsed`, Celery worker, PostgreSQL, Redis и MinIO работают вместе корректно.

## Частые проблемы

- `curl /health` не отвечает - проверьте, что `uvicorn` запущен на порту `8000`.
- UI загружается, но API падает - проверьте backend и rewrite в `frontend/next.config.mjs`.
- Документ висит на анализе - проверьте Celery worker и Redis.
- Ошибка подключения к базе - проверьте `docker compose ps`, порт `5432` и миграции `uv run alembic upgrade head`.
- Ошибка S3/MinIO - проверьте контейнер `minio`, порт `9000` и доступность `http://localhost:9001`.
- После изменения моделей база ведёт себя странно - для локальной разработки можно пересоздать Docker volumes, но это удалит локальные данные:

```bash
docker compose down -v
docker compose up -d
cd backend
uv run alembic upgrade head
```
