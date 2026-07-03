# MedMind — Enterprise Page Spec

> Положен в репозиторий: `docs/ENTERPRISE_PAGE_SPEC.md`
> Реализован: 2026-07-03

---

## Контекст

Сайт medmind.pro позиционирован на индивидуальных пользователей.
Для B2B outreach к ветеринарным корпорациям (Zoetis, Elanco, IDEXX и др.)
нужна отдельная точка входа, которая говорит языком корпоративного покупателя:
HR-директора, директора по обучению, медицинского директора.

Существующий тариф «Clinic $199/mo» — база, от которой строим.

---

## Статус реализации

- [x] Страница `/enterprise` — `frontend/app/enterprise/page.tsx`
- [x] Backend endpoint `POST /api/v1/enterprise/leads`
- [x] Admin endpoint `GET /api/v1/enterprise/leads` + CSV export + status update
- [x] Миграция БД `0035_enterprise_leads`
- [x] Email-уведомление на partners@medmind.pro
- [x] Rate limiting 3 req/hour per IP
- [x] Блокировка личных email (gmail, yahoo, mail.ru и др.)
- [x] i18n: EN + RU полностью, DE/FR/ES/TR/AR (EN fallback)
- [x] Навигация: «For teams» в ArticleNav (все публичные страницы)
- [x] Админ-раздел «Enterprise Leads» в /admin
- [x] Sitemap: /enterprise добавлен (priority 0.8)
- [x] pytest: 572 passed, 0 failed

## Файлы

| Файл | Назначение |
|------|------------|
| `frontend/app/enterprise/page.tsx` | Страница `/enterprise` (client component) |
| `backend/app/api/v1/routes/enterprise.py` | API endpoint + admin endpoints |
| `backend/alembic/versions/0035_enterprise_leads.py` | Миграция БД |
| `backend/tests/test_enterprise.py` | Тесты (7 штук) |
| `frontend/locales/en.ts` | i18n ключи enterprise.* |
| `frontend/locales/ru.ts` | i18n ключи enterprise.* (RU) |
| `frontend/components/layout/ArticleNav.tsx` | Пункт «For teams» в навигации |
| `frontend/lib/sitemap-builder.ts` | /enterprise в sitemap |

## Pricing config

Цены вынесены в объект `PRICING` в `enterprise/page.tsx` — редактировать там, не в JSX.
