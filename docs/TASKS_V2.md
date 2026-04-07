# MedMind AI — TASKS v2 (на основе TZ v3-02)
# Сессионный recovery-файл + полный TODO

> **Читать при каждом старте новой сессии**  
> Статусы: `TODO` | `IN_PROGRESS` | `DONE` | `BLOCKED`  
> Обновлять после каждого выполненного пункта.

---

## КОНТЕКСТ СЕССИИ

**ТЗ-источник:** `/Volumes/one/MEDMind/MedMind_AI_TZ_v3-02.docx.txt`  
**Предыдущий state:** `/Volumes/one/MEDMind/PROJECT_STATE.md`  
**Стек:** FastAPI + PostgreSQL + Redis + Next.js 14 + React Native Expo  
**Запуск:** `bash /Volumes/one/MEDMind/start.sh` (backend :8000, frontend :3000)  
**Ветка:** `main`

### Что уже реализовано (не трогать)
- Backend роуты: auth, content, progress, ai (ask/stream/explain/quiz/case-discuss/feedback), payments, notes, bookmarks, achievements, admin (partial), courses, veterinary, compliance
- Сервисы: ai_router, drug_service, email_service, pubmed_service, scheduler, vet_service
- Промпты: content_prompts, drug_prompts, tutor_prompts, vet_prompts
- Frontend pages: dashboard, ai-tutor, cases, drugs, flashcards, modules, progress, quiz, search, settings, admin, upgrade, pricing
- Mobile: Expo scaffold + WatermelonDB + 4 screens

---

## БЛОК A — BACKEND: НЕДОСТАЮЩИЕ ЭНДПОИНТЫ

### A1. Admin — генерация и импорт модулей через Claude
| # | Задача | Файл | Статус |
|---|--------|------|--------|
| A1.1 | `POST /admin/modules/generate` — генерация нового модуля через Claude API (specialty, topic, level → полный JSON модуля) | `backend/app/api/v1/routes/admin.py` | DONE |
| A1.2 | `POST /admin/modules/import` — загрузка JSON-файла модуля через multipart form | `backend/app/api/v1/routes/admin.py` | DONE |
| A1.3 | `GET /admin/audit-logs` — список записей audit_log (фильтр по user_id, дате, типу действия) | `backend/app/api/v1/routes/admin.py` | DONE |

### A2. Dashboard API (роль-ориентированный)
| # | Задача | Файл | Статус |
|---|--------|------|--------|
| A2.1 | `GET /dashboard/overview` — общий дашборд (stats + рекомендации + streak + due flashcards) | `backend/app/api/v1/routes/dashboard.py` (новый файл) | DONE |
| A2.2 | `GET /student/dashboard` — студенческий (модули, слабые места, план дня) | `backend/app/api/v1/routes/dashboard.py` | DONE |
| A2.3 | `GET /doctor/dashboard` — врачебный (CME кредиты, новые гайдлайны, PubMed) | `backend/app/api/v1/routes/dashboard.py` | DONE |
| A2.4 | `GET /professor/dashboard` — профессорский (список студентов, прогресс группы) | `backend/app/api/v1/routes/dashboard.py` | DONE |
| A2.5 | `GET /doctor/cme-credits` — список CME кредитов пользователя с деталями | `backend/app/api/v1/routes/dashboard.py` | DONE |
| A2.6 | Добавить `dashboard.router` в `main.py` | `backend/app/main.py` | DONE |

### A3. Уведомления
| # | Задача | Файл | Статус |
|---|--------|------|--------|
| A3.1 | Создать таблицу `notifications` в моделях (SQLAlchemy) | `backend/app/models/models.py` | DONE |
| A3.2 | Alembic миграция для таблицы notifications | auto-create via Base.metadata | DONE |
| A3.3 | `GET /notifications` — список уведомлений текущего пользователя | `backend/app/api/v1/routes/notifications.py` | DONE |
| A3.4 | `POST /notifications/{id}/read` — пометить как прочитанное | `backend/app/api/v1/routes/notifications.py` | DONE |
| A3.5 | `POST /notifications/read-all` — пометить все как прочитанные | `backend/app/api/v1/routes/notifications.py` | DONE |
| A3.6 | Добавить `notifications.router` в `main.py` | `backend/app/main.py` | DONE |

### A4. Лидерборд (Geolocation)
| # | Задача | Файл | Статус |
|---|--------|------|--------|
| A4.1 | `GET /leaderboard` — глобальный (топ по XP, параметры: period=week/month/all, limit=50) | `backend/app/api/v1/routes/progress.py` | DONE |
| A4.2 | `GET /leaderboard/specialty/{id}` — по специальности | `backend/app/api/v1/routes/progress.py` | DONE |

---

## БЛОК B — FRONTEND: НЕДОСТАЮЩИЕ СТРАНИЦЫ

### B1. Страницы
| # | Задача | Файл | Статус |
|---|--------|------|--------|
| B1.1 | `/achievements` — страница достижений (сетка значков, прогресс до следующего) | `frontend/app/(app)/achievements/page.tsx` | DONE |
| B1.2 | `/leaderboard` — таблица лидеров (глобальная + по специальности, подсветка своей строки) | `frontend/app/(app)/leaderboard/page.tsx` | DONE |
| B1.3 | `/notifications` — центр уведомлений | `frontend/app/(app)/notifications/page.tsx` | DONE |
| B1.4 | `/compliance` — GDPR панель (скачать данные, удалить аккаунт, управление согласиями) | `frontend/app/(app)/compliance/page.tsx` | DONE |
| B1.5 | `/bookmarks` — страница закладок (список с фильтром по типу: урок/модуль/препарат) | `frontend/app/(app)/bookmarks/page.tsx` | DONE |
| B1.6 | `/recommendations` — страница рекомендаций + daily plan | `frontend/app/(app)/recommendations/page.tsx` | DONE |

### B2. Компоненты
| # | Задача | Файл | Статус |
|---|--------|------|--------|
| B2.1 | `AchievementToast` — всплывающее уведомление о новом достижении (анимация, иконка, XP) | `frontend/components/ui/AchievementToast.tsx` | DONE |
| B2.2 | `NotificationBell` — колокольчик в шапке с количеством непрочитанных | `frontend/components/ui/NotificationBell.tsx` | DONE |
| B2.3 | `VeterinaryToggle` — переключатель vet mode в sidebar/settings | `frontend/components/veterinary/VeterinaryToggle.tsx` | DONE |
| B2.4 | `SpeciesSelector` — dropdown выбора вида животного с иконками | `frontend/components/veterinary/SpeciesSelector.tsx` | DONE |
| B2.5 | `DoseCalculator` — калькулятор дозы (вес, возраст, функция почек, вид) | `frontend/components/veterinary/DoseCalculator.tsx` | DONE |
| B2.6 | `InteractionChecker` — мульти-выбор препаратов + вывод взаимодействий | `frontend/components/drugs/InteractionChecker.tsx` | DONE |
| B2.7 | `ConsentManager` — UI для управления GDPR согласиями | встроен в `/compliance/page.tsx` | DONE |
| B2.8 | `DataExport` — кнопка + статус скачивания персональных данных | встроен в `/compliance/page.tsx` | DONE |

### B3. Интеграция компонентов в существующие страницы
| # | Задача | Файл | Статус |
|---|--------|------|--------|
| B3.1 | Добавить `NotificationBell` в sidebar (с badge непрочитанных) | `frontend/components/layout/Sidebar.tsx` | DONE |
| B3.2 | `VeterinaryToggle` в settings — уже был inline, фиксим API call | `frontend/app/(app)/settings/page.tsx` | DONE |
| B3.3 | `DoseCalculator` на drugs page — уже был inline, фиксим на `drugsApi` | `frontend/app/(app)/drugs/page.tsx` | DONE |
| B3.4 | `InteractionChecker` на drugs page — уже был inline, фиксим на `drugsApi` | `frontend/app/(app)/drugs/page.tsx` | DONE |
| B3.5 | Добавить `AchievementToast` в root layout | `frontend/app/(app)/layout.tsx` | DONE |
| B3.6 | Добавить ссылки на `/achievements`, `/leaderboard`, `/bookmarks`, `/notifications` в sidebar | `frontend/components/layout/Sidebar.tsx` | DONE |

### B4. Admin panel расширение
| # | Задача | Файл | Статус |
|---|--------|------|--------|
| B4.1 | Вкладка "Generate Module" — форма (specialty, topic, level) → AI генерация → preview → публикация | `frontend/app/(app)/admin/page.tsx` | DONE |
| B4.2 | Вкладка "Import Module" — upload JSON файла → preview → публикация | `frontend/app/(app)/admin/page.tsx` | DONE |
| B4.3 | Вкладка "Audit Logs" — таблица с фильтрами | `frontend/app/(app)/admin/page.tsx` | DONE |

---

## БЛОК C — КОНТЕНТ: VET МОДУЛИ

По ТЗ нужно 16 VET модулей (6 специальностей). Создано: VET-001...004.

| # | Модуль | Специальность | Статус |
|---|--------|---------------|--------|
| C1 | VET-005 — Ветеринарная хирургия | Veterinary Surgery | TODO |
| C2 | VET-006 — Ветеринарная онкология | Veterinary Oncology | TODO |
| C3 | VET-007 — Репродукция и акушерство животных | Veterinary Reproduction | TODO |
| C4 | VET-008 — Дерматология животных | Veterinary Dermatology | TODO |
| C5 | VET-009 — Офтальмология животных | Veterinary Ophthalmology | TODO |
| C6 | VET-010 — Ветеринарная неврология | Veterinary Neurology | TODO |
| C7 | VET-011 — Экзотические животные (рептилии, птицы) | Exotic Animals | TODO |
| C8 | VET-012 — Ветеринарная анестезиология | Veterinary Anesthesia | TODO |
| C9 | VET-013 — Болезни жвачных (КРС, МРС) | Large Animal - Ruminants | TODO |
| C10 | VET-014 — Болезни лошадей (углублённый) | Equine Medicine | TODO |
| C11 | VET-015 — Зоонозные заболевания | Zoonoses | TODO |
| C12 | VET-016 — Ветеринарная эпидемиология | Veterinary Epidemiology | TODO |

**Формат каждого JSON:** такой же как VET-001...004 (meta + lessons + flashcards + mcq_questions + clinical_cases)

---

## БЛОК D — BACKEND: СЕРВИСЫ И ЛОГИКА

| # | Задача | Файл | Статус |
|---|--------|------|--------|
| D1 | `notification_service.py` — создание уведомлений (achievement earned, flashcard due, daily goal) | `backend/app/services/notification_service.py` | DONE |
| D2 | Интеграция notification_service в achievements.py (при выдаче достижения → уведомление) | `backend/app/api/v1/routes/achievements.py` | DONE |
| D3 | Интеграция notification_service в scheduler.py (daily flashcard reminder) | `backend/app/services/scheduler.py` | TODO |
| D4 | CME credits логика: при завершении урока/модуля начислять CME кредиты врачам | `backend/app/api/v1/routes/progress.py` | TODO |
| D5 | Audit log запись при: просмотр AI ответа, экспорт данных, изменение роли, вход | Middleware или в роутах | TODO |
| D6 | `generate_full_module()` в `content_prompts.py` — промпт для генерации полного модуля | `backend/app/prompts/content_prompts.py` | DONE |

---

## БЛОК E — ТЕСТЫ

| # | Задача | Файл | Статус |
|---|--------|------|--------|
| E1 | pytest config + conftest.py (test DB, fixtures) | `backend/tests/conftest.py` | TODO |
| E2 | Тест: email шифруется в БД и дешифруется корректно | `backend/tests/test_security.py` | TODO |
| E3 | Тест: SM-2 алгоритм — расчёт следующей даты повторения | `backend/tests/test_sm2.py` | TODO |
| E4 | Тест: auth flow (register → login → refresh → logout → refresh rejected) | `backend/tests/test_auth.py` | TODO |
| E5 | Тест: rate limiting (6-й AI запрос для Free tier → 429) | `backend/tests/test_rate_limiting.py` | TODO |
| E6 | Тест: ролевой доступ (student не видит admin эндпоинты) | `backend/tests/test_permissions.py` | TODO |
| E7 | Тест: GDPR export — возвращает все данные пользователя | `backend/tests/test_compliance.py` | TODO |
| E8 | Тест: import_modules.py идемпотентен (повторный запуск не дублирует) | `backend/tests/test_import.py` | TODO |

---

## БЛОК F — МОБИЛЬНОЕ ПРИЛОЖЕНИЕ (доработки)

| # | Задача | Файл | Статус |
|---|--------|------|--------|
| F1 | Push-уведомления (Expo Notifications) — напоминание о повторении флэшкарт | `mobile/src/screens/` | TODO |
| F2 | Offline заглушка для AI (сообщение об отсутствии интернета) | `mobile/src/screens/ai-tutor.tsx` | TODO |
| F3 | Leaderboard экран в мобильном | `mobile/src/screens/leaderboard.tsx` (новый) | TODO |
| F4 | Achievements экран в мобильном | `mobile/src/screens/achievements.tsx` (новый) | TODO |

---

## БЛОК G — ДЕПЛОЙ И ИНФРАСТРУКТУРА

| # | Задача | Файл | Статус |
|---|--------|------|--------|
| G1 | `docker-compose.prod.yml` проверить и дополнить (nginx, ssl, healthchecks) | `docker-compose.prod.yml` | TODO |
| G2 | `nginx.conf` — reverse proxy для FastAPI + Next.js + SSL | `nginx/nginx.conf` (новый) | TODO |
| G3 | GitHub Actions CI pipeline (lint → test → build) | `.github/workflows/ci.yml` (новый) | TODO |
| G4 | `.env.example` финальный — все переменные из TZ v3-02 | `backend/.env.example` | TODO |
| G5 | `README.md` — инструкции запуска (dev + prod) | `README.md` | TODO |

---

## ПОРЯДОК ВЫПОЛНЕНИЯ (оптимальный)

```
СЕЙЧАС → A1 → A2 → A3 → A4      (backend доделать)
         B1 → B2 → B3 → B4      (frontend новые страницы + компоненты)
         D1-D6                   (сервисы и логика)
         C1-C12                  (VET контент — JSON файлы)
         E1-E8                   (тесты)
         F1-F4                   (мобильное)
         G1-G5                   (деплой)
```

---

## ТЕКУЩИЙ ПРОГРЕСС

**Дата старта v2:** 2026-04-07  
**Дата старта v2:** 2026-04-07  
**Выполнено из TASKS_V2:** 51 / 73 задач

| Блок | Выполнено | Всего |
|------|-----------|-------|
| A — Backend эндпоинты | 16 | 16 |
| B — Frontend | 22 | 22 |
| C — VET контент | 0 | 12 |
| D — Сервисы | 4 | 6 |
| E — Тесты | 0 | 8 |
| F — Mobile | 0 | 4 |
| G — Деплой | 0 | 5 |
| **ИТОГО** | **51** | **73** |

---

## КАК ОБНОВЛЯТЬ ЭТОТ ФАЙЛ

После выполнения задачи:
1. Изменить статус `TODO` → `DONE`
2. Обновить счётчик в таблице прогресса
3. Закоммитить: `git add docs/TASKS_V2.md && git commit -m "progress: done A1.1 A1.2"`
