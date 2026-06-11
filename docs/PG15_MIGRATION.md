# Миграция на PostgreSQL 15 + pgvector

## Статус

**Выполнено** — `docker-compose.yml` уже использует `pgvector/pgvector:pg15`.
pgvector доступен по умолчанию в dev-окружении.

---

## Что изменилось (Phase 0)

В `docker-compose.yml` образ обновлён с `postgres:9.6` → `pgvector/pgvector:pg15`.
Это дало:
- PostgreSQL 15 с полной поддержкой pgvector
- Расширение `vector` создаётся автоматически через alembic-миграцию
- Убрана переменная `PGVECTOR_ENABLED` — pgvector всегда включён в dev

---

## Миграция существующих данных (если была PG 9.6)

Если у вас было работающее dev-окружение на PG 9.6, выполните:

```bash
# 1. Экспорт данных со старой БД
docker exec medmind_postgres pg_dump -U medmind medmind > backup_pg9.sql

# 2. Остановить контейнеры
docker compose down

# 3. Удалить старый volume (ВНИМАНИЕ: удаляет данные!)
docker volume rm medmind_postgres_data

# 4. Поднять новые контейнеры с PG 15
docker compose up -d postgres

# 5. Дождаться старта (healthcheck)
docker compose ps

# 6. Применить миграции
cd backend && alembic upgrade head

# 7. Импортировать модули заново
cd backend && python -m app.scripts.import_modules

# 8. Если нужны пользовательские данные — восстановить из бэкапа:
# docker exec -i medmind_postgres psql -U medmind medmind < backup_pg9.sql
```

---

## Проверка pgvector

```bash
docker exec medmind_postgres psql -U medmind -d medmind -c "\dx vector"
# Должно показать: vector | ... | vector data type and ivfflat and hnsw access methods
```

---

## Alembic-миграция для pgvector

В первой миграции (`alembic/versions/0001_initial_schema.py`) должно быть:

```python
from alembic import op

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # ... остальные таблицы
```

---

## Чистая установка (с нуля)

```bash
git clone <repo>
cp backend/.env.example backend/.env
# Заполнить .env (DATABASE_URL, ANTHROPIC_API_KEY, JWT_SECRET_KEY, etc.)
make setup
# Готово — PG 15 + pgvector + все миграции + модули
```
