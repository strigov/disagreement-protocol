---
slug: buro-redesign
created: 2026-09-30
status: done
phases:
  - id: Ф1
    scope: "Фундамент «Бюро»: локальные шрифты, токены и темы, иконки, ui-примитивы, оболочка"
    status: done
  - id: Ф2
    scope: "Входной поток: главная с недавними документами, анализ, стороны, экспорт"
    status: done
  - id: Ф3
    scope: "Рабочее пространство протокола на «Бюро» и разбиение ProtocolTable без изменения поведения"
    status: done
  - id: Ф4
    scope: "UX проверки протокола: меню действий, подтверждение исключения, фильтр со счётчиками, «Проверено — дальше»"
    status: done
---

> Реализовано напрямую, без ревью плана и кода в dev-orchestrator (по решению пользователя). Отступления от плана: legacy-классы `globals.css` удалены сразу, без промежуточной перекраски (C13) и без временного allowlist в `design-tokens.test.ts`. Ф3 и Ф4 выполнены одним проходом. Цифры выравнены глобально (`'lnum'`), потому что Cormorant по умолчанию рисует старостильные.

# Disagreement Protocol — редизайн на дизайн-системе «Бюро»

## Goal

Перевести весь frontend на визуальный язык «Бюро» из strigov-crm (тёплая бумага днём, углевой фон с янтарём вечером, три гарнитуры с закреплёнными ролями, семантические токены, светлая и тёмная темы) и заодно закрыть конкретные UX-пробелы рабочего процесса: нельзя вернуться к ранее загруженному договору, непонятно, почему недоступно «Построить протокол», строка протокола исключается без подтверждения, меню действий строки не закрывается по Esc и клику вне, проверка длинного протокола требует двух отдельных действий на пункт, фильтр не показывает объём работы, а состояния загрузки и ошибок не соответствуют системе (нет skeleton и кнопки повтора).

Работа нужна сейчас, потому что пользователь явно попросил «улучши ux, переделай ui, используй для этого дизайн-систему strigov-crm», а текущая вёрстка — набор ручных глобальных классов с сине-серой палитрой, которую нельзя ни перекрасить по токенам, ни перевести в тёмную тему. План сохраняет стек (Next.js App Router, React 19, Tailwind 3.4) и всю логику сохранности данных, не добавляет зависимостей и не трогает backend.

## Acceptance criteria

List 3–7 externally observable criteria that define "done" for the whole plan. Reviewers may block only on these criteria, stated user requirements, repo constraints, or high-materiality risks.

- Все экраны (`/`, `/documents/{id}/analysis`, `/documents/{id}/parties`, `/documents/{id}/protocol` в режимах «По пунктам» и «Таблица», диалог экспорта и `/documents/{id}/export`) оформлены токенами и иерархией «Бюро»: заголовки страниц — Cormorant Garamond, интерфейс — Inter Tight, рубрики/номера/даты — JetBrains Mono uppercase-рубриками; шрифты отдаются как `/fonts/*.woff2` с того же origin, внешних запросов нет, `frontend/public/fonts/OFL.txt` содержит copyright всех трёх семейств и полный текст SIL OFL 1.1.
- В шапке есть переключатель темы («Светлая тема» / «Тёмная тема» / «Как в системе»); выбор хранится в `localStorage['disprot.theme']`, применяется до первой отрисовки (перезагрузка в тёмной теме не мигает светлой), обе темы корректны на всех экранах; на `<html>` всегда стоят `data-concept="buro"` и `data-theme="light|dark"`.
- `frontend/__tests__/design-tokens.test.ts` проходит без allowlist: в `app/**/*.tsx` и `components/**/*.tsx` нет палитровых классов Tailwind (`slate-*`, `blue-*`, …, `white`/`black`), произвольных `[…]`-значений и вариантов, hex-цветов, модификатора `dark:`, градиентов/blur, радиусов больше 12px и трёх точек после кириллицы; в `app/globals.css` цвета встречаются только внутри двух блоков токенов, а собственные классы — только `skip-link`, `rubric`, `wrap-anywhere`.
- Главная показывает «Недавние документы», открытые в этом браузере (название, этап, дата), переход идёт через `/documents/{id}/analysis` и попадает на нужный этап без перестроения протокола; на экране сторон при неактивной «Построить протокол» перечислены все невыполненные условия.
- В протоколе: меню действий строки закрывается по Esc (фокус возвращается на кнопку меню), по клику вне и после выбора, в режиме «Таблица» не обрезается контейнером; «Исключить из протокола» выполняется только после подтверждения в диалоге; фильтр показывает счётчики «Все пункты / Требуют внимания / Не проверены мной»; «Проверено — дальше» ставит отметку с прежним fingerprint в `localStorage['protocol-review:<protocolId>']` и открывает следующий пункт.
- Загрузка данных сторон и протокола показывает Skeleton и текст статуса; ошибки загрузки анализа, сторон и протокола показывают текст и кнопку «Повторить», которая повторяет запрос (протокол при повторе снова начинается со списка, существующий протокол не перестраивается).
- Все существующие тесты проходят (изменены только места, перечисленные в фазах), добавлены тесты новых сценариев; `npm run lint`, `npx tsc --noEmit`, `npm test`, `npm run build` проходят; `frontend/package.json`, `frontend/package-lock.json`, `frontend/middleware.ts` и `backend/` не изменены; порядок API-вызовов, save/flush-гейтинг, `beforeunload`, двухпроходный PATCH сторон и a11y-механика (skip link, landmarks, aria-live, клавиатурное редактирование ячеек, reduced motion) сохранены.

## Non-goals / deferred

List explicit exclusions. Reviewers MUST classify requests for these as `REJECTED_BY_SCOPE` or `DEFER` unless the orchestrator authorizes scope expansion.

- Любые изменения backend, включая endpoint `GET /api/documents` со списком документов: для локального однопользовательского приложения список «недавних документов» ведётся в браузере; серверный реестр, удаление документов с диска и управление `backend/data` из UI отложены.
- «Отменить» после исключения строки: backend не умеет восстанавливать строку, а воссоздание через `addRow` + `patchRow` теряет `source_clause_key`, `confidence` и `flags`; вместо undo — обязательное подтверждение.
- Клавиатурные сочетания для навигации по пунктам (J/K, Alt+↑/↓ и т. п.): конфликтуют с редактируемыми ячейками и требуют отдельного решения по WCAG 2.1.4.
- Изменение палитры/токенов «Бюро», в том числе контраста светлой primary-кнопки (4,1:1): это правка дизайн-системы в strigov-crm, здесь токены копируются дословно.
- Перенос стека CRM: Radix, CVA, clsx/tailwind-merge, react-router, tRPC, cmdk, QuickCapture/FAB, нижняя навигация, PWA/service worker, Toast, CommandPalette, Storybook.
- Подтверждение для «Поменять стороны», сводка проверки в диалоге экспорта, изменения формата или типографики экспортируемого DOCX.
- Перевод загрузки данных на `@tanstack/react-query` (пакет есть в зависимостях, но не используется), английская локализация, визуальные snapshot/E2E-тесты (Playwright и т. п.).
- Перевод текстов ошибок backend (например, «Document not found» из FastAPI остаётся как есть и показывается через существующую обработку `lib/api.ts`).

## Global Constraints

List the spec's project-wide requirements — version floors, dependency limits, naming and copy rules, platform requirements — one line each, with exact values copied verbatim from the spec or user request. If the spec imposes none, write literally `None declared in the spec.`

- Запрос пользователя: «улучши ux, переделай ui, используй для этого дизайн-систему strigov-crm».
- Источник истины дизайн-системы: `strigov-crm/apps/web/CLAUDE.md`, `strigov-crm/docs/adr/0001-design-system-buro.md`, `strigov-crm/apps/web/src/index.css`, `strigov-crm/apps/web/tailwind.config.ts`, `strigov-crm/apps/web/public/fonts/*.woff2`.
- Adopt the visual language, tokens, fonts, icon approach, component conventions, state conventions and copy rules; do NOT import strigov-crm's stack assumptions (not Vite + react-router + tRPC; no Radix and no CVA today); CRM-specific domain rules (matters, clients, terminology table, QuickCapture, bottom nav, PWA) do not apply.
- Стек не меняется: Next.js 15.5.24 (App Router), React 19.2.8, TypeScript 5.9.3 (`strict: true`), Tailwind 3.4.19, lucide-react 1.48.0, vitest 4.1.11 + @testing-library/react 16.3.3 + msw + jsdom 25, Node `>=22.19.0`.
- Frontend only, unless a UX improvement genuinely requires a backend change — этот план backend не меняет.
- Local-only app, privacy first: no CDNs, no Google Fonts, no external requests; fonts must be self-hosted under `frontend/public/`; OFL licensing of the copied fonts is respected.
- No new runtime dependencies without an explicit justification in the plan (dev dependencies likewise); lockfile `frontend/package-lock.json` is tracked — план не добавляет ни одной зависимости.
- Token discipline: no raw hex / Tailwind palette colours (`slate-*`, `zinc-*`, `blue-*`, …) and no arbitrary `[..px]` values in the final UI code; all colour via semantic tokens; light and dark themes both correct.
- `data-concept="buro"` + `data-theme="light|dark"` на `<html>`; модификатор Tailwind `dark:` не используется.
- Три гарнитуры и их роли: Cormorant Garamond (`font-serif`) — заголовки страниц, редакторские секционные заголовки, названия договоров/пунктов; Inter Tight (`font-sans`) — весь UI, заголовки диалогов; JetBrains Mono (`font-mono`) — номера, даты, uppercase-рубрики. Четвёртое семейство запрещено.
- Скругления `rounded-xs/sm/md/lg/pill` = 4/6/8/12/999px; тени только `shadow-sm` и `shadow-md`; без градиентов, glassmorphism, blur-фонов; радиус больше 12px на карточках и кнопках запрещён.
- Иконки только через `<Icon />` (собственные глифы `Ico` + fallback на lucide-react); размер по умолчанию 14px, stroke 1.4; другие icon-библиотеки и декоративные SVG запрещены.
- Russian copy, no emojis, "…" character not three dots, мы-форма for in-progress buttons ("Сохраняем…"); заголовки разделов — серифом с заглавной буквы, без двоеточия; метки рубрик — моно uppercase.
- Preserve all existing behaviour and data-safety logic: API calls and their order, the save/flush gating in `ProtocolTable` (`saveAll`, pending/draft refs, blocking structural ops and navigation until saves finish), `beforeunload` guard, reviewed-marks fingerprinting in localStorage `protocol-review:<protocolId>`, the exhaustive status handling on the analysis page, API error message handling in `lib/api.ts`, the two-pass parties PATCH, not rebuilding an existing protocol.
- Accessibility must not regress: skip link, landmarks, labels, roles, `aria-live` status, focus-visible styling, keyboard operation of editable cells (Enter/Space/F2 to edit, Esc cancel, Ctrl/⌘+Enter save), `prefers-reduced-motion`.
- Existing tests must keep passing; update a test only where copy/markup intentionally changes, and add tests for new UX behaviour.
- Desktop-first but must remain usable at narrow widths (current breakpoints 1000px / 700px; don't regress mobile).
- Проверка каждой фазы из `frontend/`: `npm run lint` (eslint, `--max-warnings 0`), `npx tsc --noEmit`, `npm test`, `npm run build`; визуальная проверка светлой и тёмной темы в запущенном dev-сервере.

## Files

### Ф1 — фундамент

- Create `frontend/public/fonts/CormorantGaramond-{Light,Regular,Medium,SemiBold,Bold}.woff2`, `InterTight-latin.woff2`, `InterTight-cyrillic.woff2`, `JetBrainsMono-{Regular,Medium}.woff2` — побайтовые копии шрифтов из strigov-crm.
- Create `frontend/public/fonts/OFL.txt` — copyright трёх семейств + полный текст SIL OFL 1.1.
- Modify `frontend/app/globals.css` — `@font-face`, токены (`:root`, light, dark), базовые правила, `.rubric`/`.wrap-anywhere`, перекраска legacy-классов в токены.
- Modify `frontend/tailwind.config.ts` — семантические цвета, шрифты, радиусы, тени, `text-2xs`, `tracking-rubric`.
- Modify `frontend/app/layout.tsx` — атрибуты `<html>`, inline-скрипт темы до первой отрисовки, skip link.
- Create `frontend/lib/cn.ts` — склейка классов без зависимостей.
- Create `frontend/lib/theme.ts` — режимы темы, чтение/запись, разрешение, применение, init-скрипт.
- Create `frontend/components/icons/Ico.tsx` — собственные глифы «Бюро» (`search`, `plus`, `sun`, `moon`, `chevron-right`, `x`).
- Create `frontend/components/icons/Icon.tsx` — единый `<Icon>`: `Ico` или явный реестр lucide.
- Create `frontend/components/ui/Button.tsx` — `Button`, `IconButton`, `buttonClassName`.
- Create `frontend/components/ui/Badge.tsx` — бейдж с семантическими тонами.
- Create `frontend/components/ui/Field.tsx` — единый лейбл поля.
- Create `frontend/components/ui/Input.tsx`, `frontend/components/ui/Textarea.tsx` — поля ввода на токенах.
- Create `frontend/components/ui/Skeleton.tsx` — skeleton-блок.
- Create `frontend/components/ui/States.tsx` — `EmptyState`, `ErrorState` (с повтором).
- Create `frontend/components/ui/Notice.tsx` — инлайн-уведомление с тоном.
- Create `frontend/components/ui/Dialog.tsx` — модальный диалог на нативном `<dialog>`.
- Create `frontend/components/ui/PageHeader.tsx` — редакторская шапка страницы (рубрика, serif-заголовок, описание, мета, действия).
- Create `frontend/components/ui/ThemeToggle.tsx` — переключатель темы.
- Modify `frontend/components/WorkspaceShell.tsx` — шапка (wordmark, «локально», тема), степпер, `<main>` на токенах.
- Modify `README.md` — раздел об оформлении, темах и лицензии шрифтов.
- Test `frontend/__tests__/Theme.test.tsx` — theme API, init-скрипт, переключатель.
- Test `frontend/__tests__/ui.test.tsx` — Dialog, ErrorState, Notice, Icon, Button.
- Test `frontend/__tests__/WorkspaceShell.test.tsx` — степпер, навигация, переключатель в шапке.
- Test `frontend/__tests__/design-tokens.test.ts` — механическая проверка токен-дисциплины (с временным allowlist legacy-файлов).

### Ф2 — входной поток

- Create `frontend/lib/format.ts` — `fmtDateTime` по правилам «Бюро».
- Create `frontend/lib/recent-documents.ts` — список недавних документов в `localStorage`.
- Create `frontend/components/RecentDocuments.tsx` — секция «Недавние документы» на главной.
- Modify `frontend/app/page.tsx` — главная на `PageHeader`, загрузка, недавние документы, шаги.
- Modify `frontend/components/FileUpload.tsx` — оформление, запись в недавние после загрузки.
- Modify `frontend/app/documents/[id]/analysis/page.tsx` — оформление, повтор при ошибке, запись в недавние.
- Modify `frontend/app/documents/[id]/parties/page.tsx` — оформление, Skeleton, повтор, перечень невыполненных условий, запись в недавние.
- Modify `frontend/components/PartySelector.tsx` — карточки сторон на примитивах.
- Modify `frontend/components/AnalysisSummary.tsx` — сводка обработки на токенах.
- Modify `frontend/app/documents/[id]/export/page.tsx` — страница экспорта на `PageHeader`.
- Modify `frontend/components/ExportDialog.tsx` — диалог экспорта на `Dialog`.
- Modify `frontend/components/ExportForm.tsx` — форма экспорта на примитивах.
- Modify `frontend/app/globals.css` — удаление legacy-классов без потребителей.
- Modify `README.md` — «Как пользоваться»: недавние документы и подсказка условий.
- Test `frontend/__tests__/recent-documents.test.ts`, `frontend/__tests__/format.test.ts`, `frontend/__tests__/RecentDocuments.test.tsx` — новые.
- Test `frontend/__tests__/AnalysisPage.test.tsx`, `PartiesPage.test.tsx`, `FileUpload.test.tsx`, `PartySelector.test.tsx`, `design-tokens.test.ts` — дополнения и одно намеренное изменение селектора.

### Ф3 — рабочее пространство протокола

- Create `frontend/components/protocol/types.ts` — общие типы протокольных компонентов.
- Create `frontend/components/protocol/ProtocolToolbar.tsx` — переключатель режимов и действия.
- Create `frontend/components/protocol/ClauseSidebar.tsx` — поиск, фильтр, список пунктов, прогресс.
- Create `frontend/components/protocol/ClauseFocusView.tsx` — выбранный пункт в режиме «По пунктам».
- Create `frontend/components/protocol/ProtocolGrid.tsx` — режим «Таблица».
- Modify `frontend/components/ProtocolTable.tsx` — остаётся контейнером состояния и сохранения; разметка вынесена в компоненты выше.
- Modify `frontend/components/DiffText.tsx` — подсветка различий на токенах.
- Modify `frontend/app/documents/[id]/protocol/page.tsx` — шапка, проверка полноты, Skeleton, повтор, запись в недавние.
- Modify `frontend/tailwind.config.ts` — именованные layout-токены рабочей области.
- Modify `frontend/app/globals.css` — удаление всех оставшихся legacy-классов, кроме правил временного меню строки.
- Test `frontend/__tests__/ProtocolPage.test.tsx` — дополнения (повтор, запись в недавние); `frontend/__tests__/design-tokens.test.ts` — пустой allowlist TSX и проверка классов `globals.css`.

### Ф4 — UX проверки протокола

- Create `frontend/components/protocol/RowActions.tsx` — поповер действий строки (portal, Esc, клик вне).
- Create `frontend/components/protocol/ClauseFilter.tsx` — фильтр со счётчиками.
- Create `frontend/components/ui/ConfirmDialog.tsx` — диалог подтверждения на `Dialog`.
- Modify `frontend/components/ProtocolTable.tsx` — подтверждение исключения, счётчики, «Проверено — дальше».
- Modify `frontend/components/protocol/ClauseSidebar.tsx`, `ClauseFocusView.tsx`, `ProtocolGrid.tsx` — подключение новых элементов.
- Modify `frontend/app/globals.css` — удаление правил временного меню строки.
- Modify `README.md` — шаги 5–7 «Как пользоваться».
- Test `frontend/__tests__/ProtocolActions.test.tsx` — новый.
- Test `frontend/__tests__/ProtocolPage.test.tsx`, `ReviewRegressions.test.tsx`, `Workspace.test.tsx` — намеренные изменения селекторов меню/фильтра и шаг подтверждения; `frontend/__tests__/design-tokens.test.ts` — финальный набор разрешённых CSS-классов.

## Contracts

### C1. Решения по адаптации стека (фиксированы для всех фаз)

| Вопрос | Решение | Обоснование |
|---|---|---|
| Шрифты | `frontend/public/fonts/*.woff2` + `@font-face` в `globals.css`, не `next/font/local` | Требование спецификации (self-hosted under `frontend/public/`), паритет с ADR-0001 (токены живут в CSS), без build-обработки. |
| Middleware и `/fonts/*` | `middleware.ts` не меняется | Matcher пропускает `/fonts/*` через проверку Host/Origin; same-origin GET шрифта с `Host: localhost|127.0.0.1` проходит (Origin, если отправлен, совпадает с разрешённым origin страницы). Проверяется `curl` в Ф1. |
| Тема без вспышки под SSR | inline-скрипт в `<head>` корневого layout + `suppressHydrationWarning` на `<html>` | Единственный способ выставить `data-theme` до первой отрисовки без зависимостей; `next/script beforeInteractive` в App Router ставит скрипт в очередь runtime и не гарантирует pre-paint. CSP в проекте нет (`next.config.mjs` без headers, middleware их не ставит); скрипт — статическая строка без пользовательских данных. |
| Режим по умолчанию | `system` (ADR-0001: системное предпочтение + ручной переключатель) | — |
| `cn` | локальная функция filter+join, без `clsx`/`tailwind-merge` | Нулевые зависимости. Следствие-правило: `className` вызывающей стороны не переопределяет свойство, уже заданное примитивом (нет merge конфликтов); для отличий используются props (`variant`, `size`). |
| Варианты компонентов | объекты `Record<Variant, string>` (как `Badge` в CRM), без CVA | Нет зависимости, тот же API. |
| Диалоги | нативный `<dialog>` (`showModal`, событие `cancel`), без Radix | Уже используется `ExportDialog`; нативный focus trap и Esc; fallback `setAttribute("open")` для jsdom сохраняется. |
| Иконки | `Ico` (6 используемых глифов, дословно из CRM) + **явный** реестр именованных импортов lucide | `import * as lucide` из CRM-обёртки ломает tree-shaking (≈4200 иконок в клиентском бандле); явный реестр даёт типизированный `IconName`. Все имена проверены по typings lucide-react 1.48.0. |
| Поповер меню строки | собственный disclosure-поповер через `createPortal` в `document.body`, `position: fixed` по координатам кнопки | Контейнер таблицы `overflow: auto` обрезает абсолютный поповер; Popover API/anchor positioning не поддерживаются jsdom и не везде в браузерах. |
| Недавние документы | `localStorage` без backend | Спецификация предпочитает frontend-only; вход через экран анализа, который сам маршрутизирует по статусу. |
| Контраст | см. C12 | Токены DS копируются дословно, текстовые пары выбираются с контрастом AA. |

### C2. `frontend/app/globals.css` (Ф1; конечное состояние — Ф4)

Порядок файла:

1. `@tailwind base; @tailwind components; @tailwind utilities;`
2. Девять `@font-face` — дословная копия `strigov-crm/apps/web/src/index.css` строк 8–82: `'Inter Tight'` (`font-weight: 300 700`, два файла `InterTight-latin.woff2`/`InterTight-cyrillic.woff2` с `unicode-range` как в источнике), `'Cormorant Garamond'` 300/400/500/600/700, `'JetBrains Mono'` 400/500; везде `font-display: swap; src: url('/fonts/<file>') format('woff2')`.
3. Токены — дословно, плюс `color-scheme` в блоках тем:

```css
:root {
  --font-sans: 'Inter Tight', 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
  --font-serif: 'Cormorant Garamond', Georgia, serif;
  --font-mono: 'JetBrains Mono', ui-monospace, 'SFMono-Regular', Menlo, monospace;
  --r-xs: 4px; --r-sm: 6px; --r-md: 8px; --r-lg: 12px; --r-pill: 999px;
  --sp-1: 4px; --sp-2: 8px; --sp-3: 12px; --sp-4: 16px; --sp-5: 20px; --sp-6: 24px; --sp-7: 32px; --sp-8: 40px;
}
[data-concept='buro'][data-theme='light'] {
  color-scheme: light;
  --bg: #faf6ee; --bg-elev: #ffffff; --bg-sunk: #f1ecdf;
  --bg-hover: rgba(58, 42, 18, 0.05); --bg-active: rgba(58, 42, 18, 0.09);
  --ink: #28201a; --ink-1: #4a3f33; --ink-2: #7a6e5e; --ink-3: #a89c89;
  --line-c: rgba(58, 42, 18, 0.1); --line-strong: rgba(58, 42, 18, 0.2);
  --accent: #a86a1f; --accent-soft: #f3e3cb; --accent-ink: #faf6ee;
  --warn: #a86a1f; --warn-soft: #f3e3cb; --danger: #9a3a25; --danger-soft: #f3dccf; --ok: #466a3d; --ok-soft: #dfe8d4;
  --shadow-sm: 0 1px 0 rgba(58, 42, 18, 0.04);
  --shadow-md: 0 1px 2px rgba(58, 42, 18, 0.06), 0 6px 18px rgba(58, 42, 18, 0.07);
}
[data-concept='buro'][data-theme='dark'] {
  color-scheme: dark;
  --bg: #1c1814; --bg-elev: #25211a; --bg-sunk: #14110d;
  --bg-hover: rgba(255, 238, 205, 0.05); --bg-active: rgba(255, 238, 205, 0.09);
  --ink: #f4ebd6; --ink-1: #d4c8ad; --ink-2: #968a73; --ink-3: #645a48;
  --line-c: rgba(255, 238, 205, 0.08); --line-strong: rgba(255, 238, 205, 0.16);
  --accent: #e0a967; --accent-soft: rgba(224, 169, 103, 0.14); --accent-ink: #1c1814;
  --warn: #e0a967; --warn-soft: rgba(224, 169, 103, 0.14); --danger: #e09581; --danger-soft: rgba(224, 149, 129, 0.14);
  --ok: #95b889; --ok-soft: rgba(149, 184, 137, 0.14);
  --shadow-sm: 0 1px 0 rgba(0, 0, 0, 0.4);
  --shadow-md: 0 1px 2px rgba(0, 0, 0, 0.4), 0 6px 22px rgba(0, 0, 0, 0.5);
}
```

Селекторы блоков пишутся ровно так (одинарные кавычки) — на них опирается `design-tokens.test.ts`.

4. Базовые правила (конечное состояние):

```css
html, body { background: var(--bg); color: var(--ink); font-family: var(--font-sans);
  font-feature-settings: 'cv11', 'ss01', 'ss03'; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }
body { font-feature-settings: 'tnum' 1; font-size: 0.875rem; line-height: 1.5; }
code, kbd, samp, pre { font-family: var(--font-mono); }
::selection { background: var(--accent-soft); color: var(--accent); }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.skip-link { position: absolute; left: 1rem; top: -4rem; z-index: 100; padding: 0.75rem 1rem;
  background: var(--bg-elev); color: var(--ink); border: 1px solid var(--line-strong);
  border-radius: var(--r-sm); box-shadow: var(--shadow-md); }
.skip-link:focus { top: 0.75rem; }
dialog::backdrop { background: color-mix(in srgb, var(--bg-sunk) 70%, transparent); }
@layer components { .rubric { @apply font-mono text-2xs uppercase tracking-rubric text-ink-2; } }
@layer utilities { .wrap-anywhere { overflow-wrap: anywhere; } }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important;
    transition-duration: .01ms !important; scroll-behavior: auto !important; }
}
```

5. Только в Ф1–Ф2: legacy-классы (`.btn`, `.notice`, `.protocol-table`, …) остаются, но все их литеральные цвета/шрифты/тени заменены токенами по C13. Каждая фаза удаляет legacy-селекторы, у которых больше нет потребителей в `app/`/`components/` (проверка `grep` перед удалением). После Ф3 остаются только правила временного меню строки (`.row-actions`, `.row-actions summary`, `.row-actions summary::-webkit-details-marker`, `.row-menu`, `.row-menu button`, `.row-menu button:hover`, `.protocol-table .row-menu`); Ф4 удаляет и их. Прежняя строка `:root { --ink:#243247; --muted…; --line…; --canvas…; --blue…; --blue-soft… }` удаляется в Ф1; ссылки на `--muted`/`--line`/`--canvas`/`--blue`/`--blue-soft` заменяются токенами «Бюро».

### C3. `frontend/tailwind.config.ts`

Ф1 (дословная карта CRM + два новых именованных токена для рубрик):

```ts
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)", "bg-elev": "var(--bg-elev)", "bg-sunk": "var(--bg-sunk)",
        "bg-hover": "var(--bg-hover)", "bg-active": "var(--bg-active)",
        ink: "var(--ink)", "ink-1": "var(--ink-1)", "ink-2": "var(--ink-2)", "ink-3": "var(--ink-3)",
        "line-c": "var(--line-c)", "line-strong": "var(--line-strong)",
        accent: "var(--accent)", "accent-soft": "var(--accent-soft)", "accent-ink": "var(--accent-ink)",
        warn: "var(--warn)", "warn-soft": "var(--warn-soft)",
        danger: "var(--danger)", "danger-soft": "var(--danger-soft)",
        ok: "var(--ok)", "ok-soft": "var(--ok-soft)",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        serif: ["var(--font-serif)", "Georgia", "serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      fontSize: { "2xs": ["0.6875rem", { lineHeight: "1rem" }] },
      letterSpacing: { rubric: "0.12em" },
      borderRadius: { xs: "var(--r-xs)", sm: "var(--r-sm)", md: "var(--r-md)", lg: "var(--r-lg)", pill: "var(--r-pill)" },
      boxShadow: { sm: "var(--shadow-sm)", md: "var(--shadow-md)" },
      borderColor: { DEFAULT: "var(--line-c)" },
    },
  },
  plugins: [],
};

export default config;
```

Ф3 добавляет только именованные layout-ключи (значения — rem-эквиваленты текущих px из `globals.css`):

```ts
gridTemplateColumns: { workbench: "15.625rem minmax(0, 1fr)", "workbench-narrow": "13.125rem minmax(0, 1fr)" },
minWidth: { "protocol-table": "55rem" },
maxHeight: { "protocol-table": "70vh", "clause-list": "37.5rem", "clause-strip": "7.5rem" },
```

Правило для всех фаз: новый размер/цвет, которого нет в теме, добавляется именованным ключом в `tailwind.config.ts`, а не классом `[…]`. Tailwind-брейкпоинты по умолчанию: правила «≤1000px» → ниже `lg`, «≤700px» → ниже `md`. Модификатор `dark:` не используется.

### C4. Тема: `frontend/lib/theme.ts`, layout, `ThemeToggle`

```ts
// frontend/lib/theme.ts — без "use client", без обращений к window на уровне модуля
export type ThemeMode = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";
export const THEME_STORAGE_KEY = "disprot.theme";
export function readThemeMode(): ThemeMode;            // нет значения, неизвестное значение или исключение хранилища → "system"
export function writeThemeMode(mode: ThemeMode): void; // исключения хранилища проглатываются
export function systemPrefersDark(): boolean;          // false, если typeof window.matchMedia !== "function"
export function resolveTheme(mode: ThemeMode, prefersDark: boolean): ResolvedTheme;
export function applyTheme(theme: ResolvedTheme): void; // <html data-theme=theme data-concept="buro">
export const THEME_INIT_SCRIPT: string;                // IIFE, никогда не бросает исключение
```

`THEME_INIT_SCRIPT` собирается из `THEME_STORAGE_KEY` через `JSON.stringify` и эквивалентен:

```js
(function () {
  var theme = "light";
  try {
    var mode = window.localStorage.getItem("disprot.theme");
    var dark = mode === "dark" || (mode !== "light" && typeof window.matchMedia === "function"
      && window.matchMedia("(prefers-color-scheme: dark)").matches);
    theme = dark ? "dark" : "light";
  } catch (e) {}
  document.documentElement.setAttribute("data-theme", theme);
  document.documentElement.setAttribute("data-concept", "buro");
})();
```

`frontend/app/layout.tsx`:

```tsx
<html lang="ru" data-concept="buro" data-theme="light" suppressHydrationWarning>
  <head><script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} /></head>
  <body><a className="skip-link" href="#main-content">К содержимому</a>{children}</body>
</html>
```

`metadata` не меняется.

```tsx
// frontend/components/ui/ThemeToggle.tsx ("use client")
export function ThemeToggle(): JSX.Element;
```

- `role="group"`, `aria-label="Тема оформления"`; три `<button type="button">` с `aria-pressed`, `aria-label` и `title`: «Светлая тема» (`sun`), «Тёмная тема» (`moon`), «Как в системе» (`monitor`).
- До монтирования (SSR и первый client render) состояние `null`, все `aria-pressed="false"`; в `useEffect` читается `readThemeMode()` и вызывается `applyTheme(resolveTheme(mode, systemPrefersDark()))`.
- Клик: `writeThemeMode(next)`, `applyTheme(resolveTheme(next, systemPrefersDark()))`, обновление состояния.
- В режиме `system` подписка на `change` у `matchMedia("(prefers-color-scheme: dark)")` (с guard на отсутствие `matchMedia`); отписка при смене режима/размонтировании.
- Никаких `role="status"`/`role="alert"` (на это опираются тесты страниц).

### C5. Иконки

```tsx
// frontend/components/icons/Ico.tsx — viewBox 0 0 14 14, stroke currentColor, strokeWidth 1.4,
// round caps/joins; path-данные дословно из strigov-crm Ico.tsx; prop size не попадает в DOM
export type IcoProps = SVGProps<SVGSVGElement> & { size?: number };
export const Ico: { search; plus; sun; moon; "chevron-right"; x } /* (p: IcoProps) => JSX.Element */;
export type IcoName = keyof typeof Ico;

// frontend/components/icons/Icon.tsx
export type LucideIconName =
  | "align-left" | "arrow-left" | "arrow-left-right" | "arrow-right" | "arrow-up-right"
  | "check" | "check-check" | "chevron-left" | "circle-alert" | "circle-check" | "download"
  | "ellipsis" | "file-text" | "file-up" | "history" | "info" | "loader-circle"
  | "lock-keyhole" | "monitor" | "table-2" | "trash-2" | "triangle-alert";
export type IconName = IcoName | LucideIconName;
export interface IconProps { name: IconName; size?: number; className?: string; label?: string }
export function Icon(props: IconProps): JSX.Element;
```

- Реестр lucide — объект с явными именованными импортами (`AlignLeft`, `ArrowLeft`, `ArrowLeftRight`, `ArrowRight`, `ArrowUpRight`, `Check`, `CheckCheck`, `ChevronLeft`, `CircleAlert`, `CircleCheck`, `Download`, `Ellipsis`, `FileText`, `FileUp`, `History`, `Info`, `LoaderCircle`, `LockKeyhole`, `Monitor`, `Table2`, `Trash2`, `TriangleAlert`); `import * as` запрещён. Имя из `Ico` имеет приоритет.
- `size` по умолчанию 14; lucide рендерится с `strokeWidth={1.4}` и `absoluteStrokeWidth` (визуально совпадает с 1.4px у `Ico`); класс `shrink-0` + `className`.
- Без `label`: `aria-hidden="true"`; с `label`: `role="img"` и `aria-label={label}`.
- Размеры: 14 (по умолчанию), 16 для панелей инструментов, максимум 20 для пустых состояний и зоны загрузки; 24 не используется.

### C6. ui-примитивы (`frontend/components/ui/*`)

```tsx
// cn.ts
export type ClassValue = string | false | null | undefined;
export function cn(...values: ClassValue[]): string; // filter(Boolean).join(" ")

// Button.tsx
export type ButtonVariant = "primary" | "ghost" | "outline" | "danger";
export type ButtonSize = "xs" | "sm" | "md";
export function buttonClassName(options: { variant: ButtonVariant; size?: ButtonSize; className?: string }): string;
export const Button: React.ForwardRefExoticComponent<
  React.ButtonHTMLAttributes<HTMLButtonElement> & { variant: ButtonVariant; size?: ButtonSize } & React.RefAttributes<HTMLButtonElement>>;
export const IconButton: React.ForwardRefExoticComponent<
  Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "children"> & { icon: IconName; label: string; size?: "sm" | "md" } & React.RefAttributes<HTMLButtonElement>>;
```

- `variant` обязателен (DS: кнопка без variant запрещена); `type` по умолчанию `"button"`; `forwardRef` с именованной функцией.
- Классы: база `inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50`; размеры `xs: h-7 px-2 text-xs`, `sm: h-8 px-2.5 text-sm`, `md (default): h-9 px-3 text-sm`; варианты — дословно DS: `primary: bg-accent text-accent-ink hover:opacity-90`, `ghost: border border-line-strong bg-transparent text-ink-2 hover:bg-bg-hover hover:text-ink`, `outline: border border-line-c bg-bg text-ink-2 hover:bg-bg-hover hover:text-ink`, `danger: bg-danger-soft text-danger hover:bg-bg-hover`.
- `IconButton`: `aria-label={label}` и `title={label}`, иконка через `<Icon name={icon} size={16} />`; `inline-grid place-items-center rounded-sm text-ink-2 hover:bg-bg-hover hover:text-ink aria-expanded:bg-bg-active disabled:opacity-50`; `sm: h-8 w-8`, `md: h-9 w-9`; остальные атрибуты (`aria-expanded`, `aria-controls`, `onClick`, `disabled`) пробрасываются.
- `buttonClassName` используется для `<Link>`/`<label>`, которые выглядят как кнопки.
- Одна `primary`-кнопка на экран.

```tsx
// Badge.tsx — дословно DS
export function Badge(props: React.HTMLAttributes<HTMLSpanElement> & { tone?: "neutral" | "ok" | "warn" | "danger" | "accent" }): JSX.Element;

// Field.tsx — <label class="block"><span class="mb-1 block text-xs font-medium text-ink-2">{label}{required && <span class="text-danger"> *</span>}</span>{children}</label>
export function Field(props: { label: string; required?: boolean; children: React.ReactNode }): JSX.Element;

// Input.tsx / Textarea.tsx — forwardRef, все атрибуты пробрасываются
export const Input: React.ForwardRefExoticComponent<React.InputHTMLAttributes<HTMLInputElement> & React.RefAttributes<HTMLInputElement>>;
export const Textarea: React.ForwardRefExoticComponent<React.TextareaHTMLAttributes<HTMLTextAreaElement> & React.RefAttributes<HTMLTextAreaElement>>;
```

- `Input`: `h-9 w-full rounded-sm border bg-bg px-3 text-sm text-ink placeholder:text-ink-2 disabled:opacity-60`; `Textarea`: `w-full resize-y rounded-sm border bg-bg px-3 py-2 text-sm leading-relaxed text-ink placeholder:text-ink-2 disabled:opacity-60` (без `min-h`: высоту задаёт вызывающий). Бордер: `border-danger`, если `aria-invalid` равен `true`/`"true"`, иначе `border-line-c`. `outline-none` не ставится — глобальное `:focus-visible` остаётся индикатором фокуса.

```tsx
// Skeleton.tsx
export function Skeleton(props: { className?: string }): JSX.Element; // <div aria-hidden="true" class="rounded-sm bg-bg-active motion-safe:animate-pulse …">

// States.tsx
export function EmptyState(props: { icon?: IconName; text: React.ReactNode; cta?: React.ReactNode; card?: boolean; className?: string }): JSX.Element;
export function ErrorState(props: {
  title?: React.ReactNode; titleLevel?: 1 | 2;          // по умолчанию 2
  text?: React.ReactNode;                               // по умолчанию «Не удалось загрузить данные. Попробуйте ещё раз.»
  onRetry?: () => void; retryLabel?: string;            // по умолчанию «Повторить»
  actions?: React.ReactNode; card?: boolean; className?: string;
}): JSX.Element;
```

- `EmptyState` — дословно DS (иконка в круге `bg-bg-sunk`, текст `text-sm text-ink-2`, `cta`); без роли.
- `ErrorState` — контейнер `role="alert"`, внутри заголовок (`h1` при `titleLevel={1}`: `font-serif text-2xl font-semibold text-ink`; `h2`: `text-base font-medium text-ink`), текст `text-sm text-ink-1`, кнопка `<Button variant="ghost" size="sm">` при `onRetry`, затем `actions`. Ровно один `role="alert"` на экземпляр.

```tsx
// Notice.tsx
export function Notice(props: {
  tone?: "neutral" | "warn" | "danger" | "ok"; title?: React.ReactNode; children?: React.ReactNode;
  role?: "alert" | "status"; id?: string; className?: string;
}): JSX.Element;
```

- `flex gap-2.5 rounded-md border border-line-c p-3 text-sm text-ink`; фон `neutral: bg-bg-sunk`, `warn: bg-warn-soft`, `danger: bg-danger-soft`, `ok: bg-ok-soft`; иконка `info`/`triangle-alert`/`circle-alert`/`circle-check` в `text-ink-2`/`text-warn`/`text-danger`/`text-ok`; заголовок `font-medium`; `children`-строка рендерится как прямой текст одного элемента (тесты используют точный `getByText`).

```tsx
// Dialog.tsx ("use client")
export function Dialog(props: {
  title: React.ReactNode; description?: React.ReactNode; onClose: () => void;
  dismissible?: boolean;      // по умолчанию true; false блокирует Esc и кнопку закрытия
  closeLabel?: string;        // по умолчанию «Закрыть»
  children: React.ReactNode; className?: string;
}): JSX.Element;
```

- Смонтирован = открыт. `useEffect`: запоминает `document.activeElement`, вызывает `showModal()` если это функция, иначе `setAttribute("open", "")`; cleanup — `close?.()` и `focus()` на запомненный элемент.
- `onCancel`: `preventDefault()`, затем `onClose()` только при `dismissible`.
- `aria-labelledby` на `h2` заголовка (`useId`), `aria-describedby` при `description`, `aria-modal="true"`.
- `w-full max-w-md rounded-lg border border-line-c bg-bg-elev p-0 text-ink shadow-md`; заголовок — `font-sans text-lg font-semibold` (DS: диалоги в sans); кнопка закрытия — `IconButton icon="x"`, `disabled={!dismissible}`. Клик по backdrop диалог не закрывает (как сейчас).

```tsx
// PageHeader.tsx (без "use client", без hooks)
export function PageHeader(props: {
  rubric?: React.ReactNode; title: React.ReactNode; description?: React.ReactNode;
  meta?: React.ReactNode; actions?: React.ReactNode;
}): JSX.Element;
```

- `<header>`: `rubric` → `<p className="rubric">`, `title` → `<h1 className="font-serif text-3xl font-semibold tracking-tight text-ink md:text-4xl">`, `description` → `text-sm leading-relaxed text-ink-2 max-w-2xl`, `meta` → строка `text-xs text-ink-2`, `actions` справа.
- Текст рубрик пишется в обычном регистре; uppercase только через CSS (скринридеры не читают по буквам).

### C7. `WorkspaceShell`

Props без изменений: `{ children: ReactNode; step?: 1 | 2 | 3; documentId?: string; wide?: boolean; onNavigate?: (href: string) => void }`; семантика `onNavigate` (кнопка вместо ссылки) не меняется.

- `<header>` (banner): wordmark — `font-serif text-xl font-semibold` «Протокол» + `.rubric` «разногласий», ведёт на `/` (через `navigate`); справа `lock-keyhole` + «Документы остаются на вашем компьютере» (текст `max-md:sr-only`) и `<ThemeToggle />`. `bg-bg-elev border-b border-line-c`.
- `<nav aria-label="Этапы работы">` со списком шагов «Документ», «Стороны», «Проверка протокола»: номера `font-mono` «01/02/03» в круге (`rounded-pill`): текущий `bg-accent text-accent-ink`, пройденный `bg-ok-soft text-ok` с `check`, будущий `border border-line-strong text-ink-2`; `aria-current="step"` на текущем шаге; пройденные шаги — ссылки/кнопки с `hover:bg-bg-hover`; разделитель `chevron-right` `text-ink-3`; ниже `sm` подписи нетекущих шагов `max-sm:sr-only`.
- `<main id="main-content">`: обычный `mx-auto max-w-4xl px-4 py-10 md:px-8 md:py-14`, широкий `mx-auto max-w-screen-2xl px-4 py-6 md:px-9`.
- Оболочка не рендерит заголовков `h1–h6` и элементов с `role="status"`/`role="alert"`.

### C8. Недавние документы и формат дат (Ф2)

```ts
// frontend/lib/format.ts
export function fmtDateTime(value: number | Date, now?: Date): string;
// тот же день → «Сегодня 16:05»; тот же год → «12 ноября 16:05»; иначе → «12 ноя 2025 16:05»
// месяцы (род. падеж): января … декабря; короткие: янв фев мар апр мая июн июл авг сен окт ноя дек; время HH:MM с ведущими нулями, локальная зона

// frontend/lib/recent-documents.ts
export type RecentStage = "analysis" | "parties" | "protocol";
export interface RecentDocument { id: string; title: string | null; stage: RecentStage; openedAt: number }
export const RECENT_DOCUMENTS_KEY = "disprot.recent-documents";
export const RECENT_DOCUMENTS_LIMIT = 8;
export function readRecentDocuments(): RecentDocument[];
export function rememberDocument(entry: { id: string; title?: string | null; stage: RecentStage }, now?: number): void;
export function forgetDocument(id: string): void;
```

- Хранится JSON-массив `RecentDocument`. `readRecentDocuments`: невалидный JSON или исключение хранилища → `[]`; элементы с пустым/нестроковым `id`, нестроковым-и-не-null `title`, неизвестным `stage` или нечисловым `openedAt` отбрасываются; результат отсортирован по `openedAt` по убыванию.
- `rememberDocument`: upsert по `id`; пустой/`null` новый `title` не затирает прежний непустой; `openedAt = now ?? Date.now()`; после вставки список обрезается до 8 самых свежих; исключения хранилища проглатываются.
- `forgetDocument` удаляет запись по `id` (только из списка; файл на диске не трогается).
- Кто записывает: `FileUpload` после успешной загрузки (`title` = имя файла без `.docx`, `stage: "analysis"`); экран анализа — один раз за монтирование, только если он остаётся конечным экраном (режимы `poll`, `failed` или неизвестный статус), `stage: "analysis"`, `title: contract_name`; экран сторон после загрузки (`stage: "parties"`); экран протокола после первой загрузки анализа (`stage: "protocol"`, Ф3).

```tsx
// frontend/components/RecentDocuments.tsx ("use client")
export function RecentDocuments(): JSX.Element | null;
```

- Читает список в `useEffect` (SSR и первый client render — `null`); при пустом списке — `null` (пустое состояние всей главной — зона загрузки).
- `<section aria-labelledby>`: `h2` «Недавние документы» (`font-serif text-xl font-semibold`, с заглавной буквы), пояснение «Список хранится только в этом браузере.»; `<ul>` строк с `border-b border-dashed border-line-c last:border-b-0`.
- Строка: `<Link href={`/documents/${id}/analysis`}>` (`hover:bg-bg-hover`) с названием (`font-serif`, `title ?? "Документ без названия"`), рубрикой этапа (`analysis` → «Обработка», `parties` → «Стороны», `protocol` → «Протокол») и датой `fmtDateTime(openedAt)` (`font-mono text-xs text-ink-2`); рядом, вне ссылки, `IconButton icon="x" label={`Убрать «${title}» из списка`}` → `forgetDocument` + обновление состояния.

### C9. Протокольные компоненты (Ф3)

Публичный API `ProtocolTable` не меняется: default export, `ProtocolTableHandle { saveAll(): Promise<boolean>; revealRow(id: string): void }`, `SaveState`, все props (`rows`, `draftingRole`, `counterpartyRole`, `busy`, `initialMode`, `storageKey`, `reviewContext`, `warnings`, `onSaveStateChange`, `onPatch`, `onDelete`, `onMerge`, `onAddRow`, `onSwapParties`).

В `ProtocolTable.tsx` остаются без изменения логики: все `useState`/`useRef`, `updateDrafts`, `draftsRef`, `pending`, `cancelled`, эффект `beforeunload`, `commit`, `saveAll`, `useImperativeHandle`, `handleEditKey`, `rowHasPendingSave`, `renderEditableText` (меняются только классы), `columns`, `isReviewed`, `filtered` (с правилом «строка с черновиком всегда видна»), `active`/`activeIndex`, `changeView`, `toggleReviewed` (снимок черновиков до flush), запись отметок в `protocol-review:<storageKey>`. Вынесенные компоненты не держат состояния сохранения и получают готовые элементы ячеек через `renderCell`: элементы создаются в рендере контейнера, как сейчас, поэтому DOM-идентичность `input`/`textarea` при наборе сохраняется.

```ts
// frontend/components/protocol/types.ts
import type { ReactNode } from "react";
import type { ProtocolRow } from "@/lib/types";
export type EditableField = "point_label" | "party_1_text" | "party_2_text" | "agreed_text";
export interface ProtocolColumn { field: EditableField; header: string; label: string }
export type ClauseFilterValue = "all" | "attention" | "unreviewed";
export type RenderCell = (row: ProtocolRow, field: EditableField, label: string) => ReactNode;
```

```tsx
export function ProtocolToolbar(props: {
  mode: "focus" | "table";
  modeDisabled: boolean;        // busy || switching
  actionsDisabled: boolean;     // busy
  onModeChange: (mode: "focus" | "table") => void;  // контейнер оборачивает в changeView
  onAddRow: () => void;
  onSwapParties: () => void;
}): JSX.Element;
// role="group" aria-label="Вид протокола", кнопки с aria-pressed «По пунктам» (align-left) / «Таблица» (table-2);
// Button ghost «Добавить строку» (plus), Button ghost «Поменять стороны» (arrow-left-right)

export function ClauseSidebar(props: {
  rows: ProtocolRow[];            // filtered
  totalCount: number;             // все строки протокола
  activeId: string | undefined;
  navDisabled: boolean;           // busy || switching
  isReviewed: (row: ProtocolRow) => boolean;
  isAttention: (row: ProtocolRow) => boolean;
  onSelect: (rowId: string) => void;
  search: ReactNode;
  filter: ReactNode;
  reviewedCount: number;
  storageNotice: boolean;
}): JSX.Element;
// <aside aria-label="Навигация по пунктам">, <nav aria-label="Пункты договора">,
// кнопки пунктов aria-label={`Открыть пункт ${label || "без номера"}`}, aria-current, текст «Пункт {label}» одним текстовым узлом-элементом,
// прогресс «Проверено вами: X из Y» + <progress aria-label="Прогресс вашей проверки"> + текст про хранение отметок

export function ClauseFocusView(props: {
  row: ProtocolRow;
  position: number;               // activeIndex + 1
  total: number;                  // filtered.length
  navDisabled: boolean;
  onPrevious: (() => void) | null;  // null → кнопка disabled
  onNext: (() => void) | null;
  actions: ReactNode;
  attention: boolean;
  rowWarnings: ValidationWarning[];
  showDiff: boolean;
  onShowDiffChange: (value: boolean) => void;
  counterpartyRole: string;
  draftingRole: string;
  counterpartyLabel: string;      // columns[1].label
  draftingLabel: string;          // columns[2].label
  renderCell: RenderCell;
  reviewed: boolean;
  reviewDisabled: boolean;        // busy || switching || saveState !== "saved"
  onToggleReviewed: () => void;
}): JSX.Element;
// <section aria-label="Выбранный пункт">; <h2 class="font-serif …">Пункт {renderCell(row, "point_label", "Пункт договора")}</h2>;
// строка позиции «{position} из {total} · Отредактирован вручную|Сформирован из правок договора»;
// IconButton «Предыдущий пункт»/«Следующий пункт»; Notice warn «Проверьте этот пункт» при attention;
// чекбокс «Подсветить различия»; панели «Контрагент»/«Наша сторона»; «Согласованная редакция»;
// футер: чекбокс «Проверено мной», Button ghost «Следующий пункт»

export function ProtocolGrid(props: {
  rows: ProtocolRow[];            // filtered
  columns: ProtocolColumn[];
  isAttention: (row: ProtocolRow) => boolean;
  renderCell: RenderCell;
  renderActions: (row: ProtocolRow) => ReactNode;
  empty: ReactNode;
  search: ReactNode;
  filter: ReactNode;
}): JSX.Element;
// одна <table> (table-fixed min-w-protocol-table) в обёртке max-h-protocol-table overflow-auto;
// <thead> со sticky <th scope="col"> и sr-only «Действия»; <tbody> содержит только строки данных
// (или одну строку с colSpan=5 и empty); строка «требует внимания» — border-l-2 border-l-warn на первой ячейке;
// значок низкой уверенности: <span aria-label={`Низкая уверенность: ${pct}%`}> с triangle-alert (text-warn)
```

Пустое состояние (формирует контейнер): `EmptyState`; при наличии строк — «Ничего не найдено.» + `Button ghost` «Сбросить фильтры»; без строк — «В протоколе пока нет строк.» и «Нажмите «Добавить строку», чтобы начать.» в одном элементе.

### C10. Компоненты Ф4

```tsx
// frontend/components/protocol/RowActions.tsx ("use client")
export function RowActions(props: {
  disabled: boolean;              // busy || rowHasPendingSave(row.id): пункты disabled, кнопка меню активна
  onMergePrevious: () => void;
  onMergeNext: () => void;
  onRequestDelete: () => void;    // открывает подтверждение у родителя; сам RowActions ничего не удаляет
}): JSX.Element;
```

- Триггер: `IconButton icon="ellipsis" label="Действия со строкой"` с `aria-expanded` и `aria-controls`.
- Открытие рендерит поповер через `createPortal(…, document.body)`: `fixed z-50 w-60 rounded-md border border-line-c bg-bg-elev p-1 shadow-md`, координаты `top/left` — inline style, вычисленные в `useLayoutEffect` из `getBoundingClientRect()` кнопки и поповера (выравнивание по правому краю кнопки, отступ 4px, при нехватке места снизу — над кнопкой, прижатие к viewport с полем 8px). Поповер без `aria-label`/`aria-labelledby` (иначе `getByLabelText("Действия со строкой")` найдёт два элемента).
- Пункты — `<button type="button">` с нативным `disabled`: «Объединить с предыдущей», «Объединить со следующей», «Исключить из протокола» (`text-danger`, иконка `trash-2`); `hover:bg-bg-hover`.
- При открытии фокус на первый активный пункт (если все disabled — на контейнер с `tabIndex={-1}`); ↑/↓/Home/End перемещают фокус по активным пунктам.
- Закрытие: Esc (фокус на триггер); `pointerdown` вне поповера и триггера; `resize` окна; `scroll` (capture) вне поповера; уход фокуса за пределы поповера и триггера; выбор пункта (сначала закрытие, затем колбэк; после merge фокус на триггер).

```tsx
// frontend/components/ui/ConfirmDialog.tsx ("use client")
export function ConfirmDialog(props: {
  title: string; description?: React.ReactNode; confirmLabel: string; cancelLabel?: string; // по умолчанию «Отмена»
  onConfirm: () => void; onCancel: () => void;
}): JSX.Element;
// на Dialog (dismissible, Esc/крестик = onCancel); кнопки: Button ghost cancelLabel с autoFocus, Button danger confirmLabel
```

Исключение строки: `RowActions.onRequestDelete` → `setPendingDelete(row)` в контейнере → `ConfirmDialog` с `title={`Исключить пункт ${row.point_label || "без номера"} из протокола?`}`, `description` «Строка и все её редакции будут удалены из протокола. Отменить это действие нельзя.», `confirmLabel` «Исключить». Подтверждение: `const id = pendingDelete.id; setPendingDelete(null); void onDelete(id);` — дальше прежний путь страницы `remove → perform → saveAll → api.deleteRow`. Отмена: `setPendingDelete(null)`, `onDelete` не вызывается.

```tsx
// frontend/components/protocol/ClauseFilter.tsx
export function ClauseFilter(props: {
  value: ClauseFilterValue;
  counts: Record<ClauseFilterValue, number>;
  layout: "stack" | "inline";     // stack — сайдбар, inline — панель таблицы
  onChange: (value: ClauseFilterValue) => void;
}): JSX.Element;
// role="group" aria-label="Фильтр пунктов"; три кнопки с aria-pressed:
// «Все пункты», «Требуют внимания», «Не проверены мной», каждая + <Badge tone="neutral"> со счётчиком (font-mono)
```

Счётчики считаются по всем строкам протокола без учёта поиска: `all = rows.length`, `attention = rows.filter((r) => needsAttention(r, warnings)).length`, `unreviewed = rows.length - reviewedCount`. Состояние `filter` в контейнере типизируется как `ClauseFilterValue`.

«Проверено — дальше» — новые обязательные props `ClauseFocusView`: `onReviewAndNext: () => void; reviewAndNextDisabled: boolean`. Кнопка `Button variant="outline"` с `check-check` и текстом «Проверено — дальше» в футере перед «Следующий пункт»; `disabled = busy || switching || saveState !== "saved" || isReviewed(active)`. Логика в контейнере:

```ts
// toggleReviewed рефакторится в общий помощник без изменения поведения:
const setReviewMark = async (row: ProtocolRow, mark: boolean, after?: () => void) => {
  // снимок черновиков строки из draftsRef ДО flush — как в текущем toggleReviewed
  // await changeView(() => { next = { ...reviewed }; mark ? next[row.id] = rowFingerprint(snapshot, reviewContext) : delete next[row.id];
  //   setReviewed(next); persist в localStorage `protocol-review:${storageKey}` (ошибка → storageNotice); after?.(); })
};
const toggleReviewed = (row: ProtocolRow) => setReviewMark(row, !isReviewed(row));
const reviewAndNext = (row: ProtocolRow) => {
  const nextId = filtered[activeIndex + 1]?.id;         // вычисляется до отметки
  return setReviewMark(row, true, () => { if (nextId) setSelectedId(nextId); });
};
```

Строка позиции в `ClauseFocusView` получает `aria-live="polite"` (без `role="status"`).

### C11. Инварианты разметки, на которые опираются тесты (все фазы)

- Тексты/имена без изменений: «Анализируем документ…», «Документ готов к проверке», «Документ не удалось обработать», «Ошибка обработки документа», «Неизвестный статус документа», «Не удалось загрузить анализ», ссылка «Загрузить другой документ» (`href="/"`), «Загружаем…», «Стороны договора», «Построить протокол», «Для протокола нужны две стороны. Добавьте недостающую или удалите лишнюю.», плейсхолдеры «Наименование»/«Роль», кнопки «Удалить», «Строим таблицу…», «Не удалось загрузить протокол», `aria-label="Экспорт DOCX"`, диалог «Скачать протокол», заголовок «Экспорт», «Имя файла (без .docx)», «Сохранить»/«Сохраняем…», «Файл: … .docx», «Скачивание началось. Проверьте загрузки браузера.», «Перетащите .docx сюда или выберите файл» (прямой ребёнок `div` зоны drop), `aria-label="Выбрать файл"`, «Таблица», «Добавить строку», «Поменять стороны», «Открыть пункт …», «Поиск по пунктам», «Выбранный пункт», «Проверено мной», «Сбросить фильтры», «В протоколе пока нет строк», «Отметки доступны только до закрытия страницы.», «Действия со строкой», «Объединить с предыдущей», «Исключить…», «Низкая уверенность: N%», «Уверенность нумерации: 82%», «Найдено правок: <strong>N</strong>».
- Метрики `AnalysisSummary` («Уверенность нумерации: …%», «Правок всего: …») остаются прямым текстом одного элемента (числа не оборачиваются в отдельные элементы).
- Номер пункта не выделяется в отдельный элемент ни в сайдбаре («Пункт 1.1» одним элементом), ни где-либо ещё, кроме редактируемого `span role="textbox"`: тесты используют `getByText("1.1")`.
- На экране анализа ровно один `role="status"` (в неошибочных состояниях) и ровно один `role="alert"` (в ошибочных). В `ProtocolTable` единственный `role="status"` — индикатор «Сохраняем…» ячейки. `Skeleton`, `ThemeToggle`, `WorkspaceShell`, строка позиции пункта ролей `status`/`alert` не имеют.
- Пока данные сторон не загружены, текст «Стороны договора» не выводится (тесты ждут его как признак загрузки).
- В режиме «Таблица» ровно одна `<table>`, в `<tbody>` только строки данных; во время загрузки страницы протокола `<table>` не рендерится.

### C12. Правила тона и контраста

- `text-ink-3` не используется для текста (2,5:1 на `bg` в обеих темах) — только для декоративных иконок и разделителей. Рубрики, мета и плейсхолдеры — `text-ink-2` (4,6:1 в светлой, 5,2:1 в тёмной). Отклонение от CRM (там рубрики в `ink-3`) сделано ради AA.
- `text-warn`/`text-accent` — только для иконок, бордеров, полос, фокус-кольца и декоративных меток (в светлой теме 4,1:1 на `bg`, 3,5:1 на `*-soft`); значимый текст на любом фоне — `text-ink`, `text-ink-1`, `text-ink-2`, `text-danger` (≥5,3:1) или `text-ok` (≥4,9:1). `Badge` с тонами `warn`/`accent` в этом плане не используется.
- Остаточное отклонение уровня DS: текст primary-кнопки `accent-ink` на `accent` в светлой теме — 4,1:1 (ниже 4,5:1 для обычного текста); токены не меняются (Non-goals), отклонение фиксируется в итоговом отчёте.
- Индикатор фокуса никогда не убирается; внутри контейнеров с `overflow-hidden` используется `focus-visible:-outline-offset-2`, чтобы кольцо не обрезалось.

### C13. Перекраска legacy-классов в Ф1 (механическая, без изменения layout)

| Было | Стало |
|---|---|
| `var(--ink)` legacy, `#344767`, `#42516a`, `#44556c`, `#475569`, `#485b76`, `#566477`, `#5b6b81`, `#60718a`, `#627086`, `#637287`, `#657386`, `#6b7787` | `var(--ink)` (Бюро) для основного текста; перечисленные серо-синие — `var(--ink-1)` |
| `var(--muted)`, `#7b8797`, `#7c8796`, `#8490a0`, `#8793a3`, `#8993a2`, `#8a96a5`, `#8b96a5`, `#939dac`, `#9aa7b9` | `var(--ink-2)` |
| `#bec6d0`, `#c7cfd9` (разделители, шевроны) | `var(--ink-3)` / `var(--line-strong)` |
| `white`, `#fff` (поверхности) | `var(--bg-elev)` |
| `var(--canvas)` | `var(--bg)` |
| `#e9edf2`, `#edf0f4` (плашки, count), `#f0f4fc`, `#f5f7fa`, `#f5f7fb`, `#fafbfd`, `#fbfcfd`, `#263f70` | `var(--bg-sunk)` |
| `#f0f3f7`, `#f0f5ff`, `#f3f6fa`, `#f7f9fc`, hover `#edf0f4` | `var(--bg-hover)` |
| `var(--line)`, `#e3e7ec`, `#eef0f3`, `#dce6fd` | `var(--line-c)` |
| `#bcc9df`, `#cad3e0`, `#d7dee7`, `#dce1e8`, `#dce3ed` | `var(--line-strong)` |
| `var(--blue)`, `#315dc6`, `#264caa`, `#547bcd`, `#789be6`, `#85a3e7`, `#8ca8e3` | `var(--accent)` (hover primary — `opacity: .9`) |
| `var(--blue-soft)`, `#edf2ff`, `#e7edfa`, `#f5f7fd` | `var(--accent-soft)` |
| текст на синем (`white` в `.btn-primary`, текущий шаг) | `var(--accent-ink)` |
| предупреждения `#ebdab7`, `#eeddb9`, `#fffbf2`, `#fffcf5`, `#866126`, `#d9ac56` | фон `var(--warn-soft)`, бордер `var(--line-c)`, текст `var(--ink)`, полоса `var(--warn)` |
| ошибки `#fff5f4`, `#f0cdca`, `#a4413d`, `#fbecec`, `#ac5757`, `#c58787` | фон `var(--danger-soft)`, текст `var(--danger)` |
| успех `#f0f8f3`, `#d1e5d7`, `#397858`, `#edf4ef`, `#438461`, `#548069`, `#e7f4eb`, `#347451` | фон `var(--ok-soft)`, текст `var(--ok)` |
| тени `#23478e12`, `#23364a12`, `#25374c17`, `#172f4829` | `var(--shadow-sm)` / `var(--shadow-md)` |
| `.export-dialog::backdrop` + `backdrop-filter: blur(3px)` | удаляется; работает общий `dialog::backdrop` |
| `font-family` у `body` | `var(--font-sans)`; `.page-title`, `.document-heading h1` — `var(--font-serif)` |

Правила `.brand*`, `.local-badge`, `.workflow*`, `.step-*`, `.workspace*`, `:root` legacy-палитра, `:focus-visible`, `::selection`, `.skip-link` заменяются правилами C2/C7 и удаляются в Ф1.

### C14. `frontend/__tests__/design-tokens.test.ts`

- Файлы: все `*.tsx` в `app/` и `components/` (обход `fs.readdirSync(dir, { recursive: true })`, корень через `fileURLToPath(new URL("..", import.meta.url))`).
- Запрещённые шаблоны (для TSX): палитра `/\b(?:bg|text|border|ring|outline|fill|stroke|from|to|via|decoration|divide|placeholder|accent|shadow|caret)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3}\b/`, `/\b(?:bg|text|border)-(?:white|black)\b/`; произвольные значения `/[a-z0-9]-\[[^\]]*\]/` (ловит и `aria-[…]`/`data-[…]`) и произвольные варианты `/\[(?:@|&)[^\]]*\]:/` (не путать с вычисляемыми ключами `{ [key]: value }`, их шаблон не задевает); hex `/#[0-9a-fA-F]{3,8}\b/`; вариант `dark:` только внутри строки классов `/(?:^|[\s"'`])dark:[a-z!-]/` (объектный ключ `dark: "…"` не совпадает); `/\bbackdrop-blur|\bblur-(?:none|sm|md|lg|xl|2xl|3xl)\b|\bbg-gradient-/`; `/\brounded-(?:xl|2xl|3xl|full)\b/`; `/\bshadow-(?:lg|xl|2xl|inner)\b/`; три точки после кириллицы `/[А-Яа-яЁё]\.\.\./`. Слово «blur» в комментариях `ProtocolTable` под эти шаблоны не попадает.
- `const LEGACY_TSX = new Set<string>([...])` — пути (относительно `frontend/`), временно освобождённые от проверки; Ф1: `app/documents/[id]/analysis/page.tsx`, `app/documents/[id]/protocol/page.tsx`, `components/AnalysisSummary.tsx`, `components/ExportForm.tsx`, `components/PartySelector.tsx`, `components/ProtocolTable.tsx`; Ф2 оставляет `app/documents/[id]/protocol/page.tsx`, `components/ProtocolTable.tsx`; Ф3 удаляет allowlist целиком.
- `globals.css` (с Ф1): после вырезания двух блоков `[data-concept='buro'][data-theme='light'|'dark'] {…}` не остаётся `#hex` и `rgba?(`; нет `@import` и `http`.
- `globals.css` (с Ф3): после удаления комментариев и `url(...)` множество классовых селекторов `/\.([a-z][a-z0-9-]*)/g` ⊆ `ALLOWED_CSS_CLASSES`. В Ф3 это `{ "skip-link", "rubric", "wrap-anywhere", "row-actions", "row-menu", "protocol-table" }` (три последних — временное меню строки на `<details>`, см. Ф3 Step 3); Ф4 сужает до `{ "skip-link", "rubric", "wrap-anywhere" }`.

## Test strategy

### Общая проверка каждой фазы

Из `frontend/` (если `node_modules` нет — сначала `npm ci`, lockfile не меняется):

```bash
npm run lint
npx tsc --noEmit
npm test
npm run build
git diff --stat -- package.json package-lock.json middleware.ts   # должно быть пусто
git diff -- tsconfig.json   # если next build переписал файл — откатить только этот автогенерированный churn
```

Визуальная проверка: из корня `./scripts/install.sh` (однократно) и `./scripts/start.sh`, открыть `http://127.0.0.1:3000`, загрузить `samples/03_complex_styles_annex_tables.docx` (замечания, предупреждения) и `samples/06_edge_broken.docx` (ошибка обработки); пройти экраны фазы в светлой и тёмной теме переключателем в шапке, на ширине ~1440px и ~375px; в DevTools → Network убедиться, что нет запросов не к `127.0.0.1:3000`.

Уровень тестов — Vitest + Testing Library + MSW (как сейчас). Не тестируются: имена CSS-классов в компонентных тестах (кроме механической проверки C14), снапшоты разметки, загрузка шрифтов в jsdom, пиксельная вёрстка; E2E в браузере не добавляется. jsdom не реализует `matchMedia`, `HTMLDialogElement.showModal` и реальные размеры (`getBoundingClientRect` → нули) — код обязан иметь guards (C4, C6), тесты стабят `matchMedia` там, где он нужен.

### Ф1

- Unit `Theme.test.tsx`: `resolveTheme` для трёх режимов; `readThemeMode` → `"system"` для пустого, неизвестного значения и бросающего `getItem`; `THEME_INIT_SCRIPT` через `new Function(THEME_INIT_SCRIPT)()` ставит `data-theme` для `dark`, `light`, `system` + застабленного `matchMedia(matches: true)`, для отсутствующего `matchMedia` и для бросающего хранилища (без исключения, `light`), и всегда `data-concept="buro"`.
- Component `ThemeToggle`: клик «Тёмная тема» → `data-theme="dark"`, `localStorage['disprot.theme'] === "dark"`, `aria-pressed="true"`; в режиме «Как в системе» событие `change` застабленного `matchMedia` переключает `data-theme`.
- Component `ui.test.tsx`: `Dialog` доступен как `dialog` с именем заголовка; событие `cancel` вызывает `onClose`, при `dismissible={false}` — нет; при размонтировании фокус возвращается на кнопку-источник. `ErrorState` — `role="alert"` содержит заголовок и текст, «Повторить» вызывает `onRetry`. `Notice` пробрасывает `role`. `Icon` без `label` — `aria-hidden="true"`, с `label` — `role="img"` с именем. `Button` по умолчанию `type="button"`.
- Component `WorkspaceShell.test.tsx`: при `step={2}` текущий шаг помечен `aria-current="step"`, шаг 1 — ссылка на `/`, шаг 3 — не ссылка; с `onNavigate` шаг 1 — кнопка, вызывающая `onNavigate("/")`; в шапке есть `group` «Тема оформления»; есть `main#main-content`.
- Mechanical `design-tokens.test.ts` (C14) с allowlist Ф1.
- Все существующие тесты проходят без изменений (разметка страниц в Ф1 не меняется, кроме оболочки).
- Ручная: `curl -sI http://127.0.0.1:3000/fonts/InterTight-cyrillic.woff2` → `200` и `content-type: font/woff2` в dev и после `npm run build && npm run start`; перезагрузка в тёмной теме без вспышки светлой.

### Ф2

- Unit `recent-documents.test.ts`: запись/чтение/удаление; сортировка по `openedAt`; обрезка до 8; невалидный JSON → `[]`; невалидные записи отбрасываются; `null`-title не затирает прежний; бросающий `setItem`/`getItem` не пробрасывает исключение.
- Unit `format.test.ts`: `fmtDateTime` для того же дня («Сегодня 09:05»), того же года («12 ноября 16:05»), другого года («12 ноя 2025 16:05») с фиксированным `now`.
- Component `RecentDocuments.test.tsx`: при пустом хранилище ничего не рендерится; записи выводятся от новых к старым, ссылка ведёт на `/documents/<id>/analysis`, видны этап и дата; «Убрать «…» из списка» убирает запись из UI и из `localStorage`.
- `AnalysisPage.test.tsx` (+2): после ответа 500 кнопка «Повторить» делает второй запрос и при `parsed` вызывает `push("/documents/<id>/parties")`, без автоповторов; для `failed` в недавних появляется запись `stage: "analysis"`. Существующие 9 тестов (включая «ровно один status/alert» и счётчики запросов) проходят без изменений.
- `PartiesPage.test.tsx` (+3): без выбранной стороны видно «Отметьте вашу сторону — от её имени будет составлен протокол.», кнопка disabled; после выбора радиокнопки подсказка исчезает и кнопка активна; очистка наименования показывает «Заполните наименование и роль каждой стороны.»; ошибка 500 → «Повторить» → стороны загружаются; после загрузки в недавних `stage: "parties"`. Существующие 4 теста без изменений.
- `FileUpload.test.tsx` (+1): после успешной загрузки в недавних `{ id: "doc-123", title: "contract", stage: "analysis" }`.
- `PartySelector.test.tsx`: намеренное изменение — `getByText("+ Добавить сторону")` → `getByRole("button", { name: "Добавить сторону" })` (декоративный «+» заменён иконкой `plus`).
- `ExportPage.test.tsx`, `ProtocolPage.test.tsx` («export opens a dialog…»), `ReviewRegressions.test.tsx` (экспорт) — без изменений, проверяют `ExportDialog` на `Dialog`.

### Ф3

- Все существующие тесты `ProtocolPage.test.tsx`, `ReviewRegressions.test.tsx` (включая DOM-идентичность и каретку при наборе, ожидание сохранения перед экспортом/удалением, `beforeunload`) и `Workspace.test.tsx` проходят **без изменений** — это основной критерий фазы «разбиение без изменения поведения».
- `ProtocolPage.test.tsx` (+2): ошибка `GET /api/protocols` → `ErrorState` «Не удалось загрузить протокол» → «Повторить» → строки отображаются, `POST /api/documents/doc1/protocol` не вызывался, если список вернул существующий протокол; после загрузки анализа в недавних `{ stage: "protocol", title: <contract_name> }`.
- `design-tokens.test.ts`: allowlist пуст, включена проверка классов `globals.css`.

### Ф4

- Component `ProtocolActions.test.tsx`:
  - Меню: открытие ставит `aria-expanded="true"` и фокус на «Объединить с предыдущей»; Esc закрывает и возвращает фокус на «Действия со строкой»; `pointerdown` вне закрывает; выбор «Объединить со следующей» закрывает и вызывает `onMerge("r1", "next")`; при сохранении строки в полёте пункты disabled.
  - Исключение: «Исключить из протокола» открывает диалог «Исключить пункт 1.1 из протокола?»; «Отмена» закрывает без `onDelete`; «Исключить» вызывает `onDelete("r1")` ровно один раз.
  - Фильтр: для строк `first` (confidence 1) и `second` (0.6) кнопки «Все пункты 2», «Требуют внимания 1», «Не проверены мной 2»; «Требуют внимания» скрывает «Открыть пункт 3.1»; после отметки пункта счётчик «Не проверены мной» уменьшается.
  - «Проверено — дальше»: на первом пункте ставит отметку (`localStorage['protocol-review:<key>'].r1 === rowFingerprint(first, ctx)`), заголовок становится «Пункт 4.2»; кнопка disabled при несохранённом черновике и для уже проверенного пункта; при фильтре «Не проверены мной» после отметки открыт следующий непроверенный пункт.
- Намеренные изменения существующих тестов:
  - `ProtocolPage.test.tsx` «row actions menu offers merge and delete»: после клика «Объединить с предыдущей» меню закрыто, поэтому меню открывается повторно, далее «Исключить из протокола» и подтверждение `within(screen.getByRole("dialog")).getByRole("button", { name: "Исключить" })`; ожидание `onDelete("r1")` прежнее.
  - `ProtocolPage.test.tsx` «merge and delete are disabled while a row save is in flight» — проверить, что проходит без изменений (кнопки пунктов остаются `button` с нативным `disabled`, меню не закрывается при завершении сохранения); менять только если падает, с объяснением.
  - `ReviewRegressions.test.tsx` «delete waits for another row's save…»: вместо `getAllByRole("button", { name: /Исключить/ })[1]` — после открытия меню второй строки `getByRole("button", { name: "Исключить из протокола" })`, затем подтверждение в диалоге; остальные ожидания (удаление ждёт сохранения, текст «9.9» сохранён) без изменений.
  - `ReviewRegressions.test.tsx` «structural request failure leaves editor mounted»: добавить шаг подтверждения.
  - `Workspace.test.tsx` «search and attention filter…»: `userEvent.selectOptions(screen.getByRole("combobox"), "attention")` → `userEvent.click(screen.getByRole("button", { name: /Требуют внимания/ }))`.
  - `design-tokens.test.ts`: `ALLOWED_CSS_CLASSES` сужен до `{ "skip-link", "rubric", "wrap-anywhere" }` (финальное состояние критерия приёмки).

## Risks / unknowns / assumptions

- **DATA_LOSS — разбиение `ProtocolTable` (Ф3).** Перенос состояния/refs в дочерние компоненты мог бы разорвать связь `draftsRef`/`pending`/`cancelled` с `saveAll` и потерять черновик. Митигация: состояние и логика сохранения не покидают контейнер (C9), дочерние компоненты получают готовые элементы через `renderCell`; неизменённые регрессионные тесты (каретка, ожидание сохранения, `beforeunload`) — критерий фазы.
- **DATA_LOSS — подтверждение исключения (Ф4).** Диалог не должен обходить `perform`: подтверждение вызывает тот же `onDelete` → `remove` → `perform` → `saveAll`; отмена ничего не вызывает. Открытие меню по-прежнему blur-ит активную ячейку и запускает её сохранение; пункты строки с сохранением в полёте disabled.
- **DATA_LOSS — недавние документы.** Переход из списка идёт только на `/documents/{id}/analysis`, который маршрутизирует по статусу; экран протокола по-прежнему сначала вызывает `listProtocolsForDocument` и строит протокол только при пустом списке, в том числе при «Повторить».
- **REGRESSION — селекторы тестов.** Тесты опираются на тексты, роли и уникальность элементов (C11); все намеренные изменения перечислены в Test strategy, прочие тесты менять нельзя. Особые ловушки: единственность `role="status"`/`role="alert"`, `getByText("1.1")`, «Стороны договора» только после загрузки, `closest("div")` у зоны загрузки.
- **REGRESSION — a11y-контраст.** Токены DS дают `ink-3` 2,5:1 и `warn`/`accent`-текст 3,5–4,1:1 в светлой теме; правила C12 не пускают их в значимый текст. Остаточный риск уровня DS — текст primary-кнопки 4,1:1; сознательно не исправляется (Non-goals) и указывается в итоговом отчёте.
- **SECURITY — inline-скрипт темы.** Статическая строка без пользовательских данных (ключ через `JSON.stringify` константы), XSS-поверхности нет; CSP сейчас нет — если её добавят, понадобится hash/nonce.
- **ASSUMPTION — приватность localStorage.** Названия договоров в `disprot.recent-documents` не покидают браузер (та же граница доверия, что у `protocol-review:*` и локальной БД). `localhost:3000` и `127.0.0.1:3000` — разные origin, поэтому списки, тема и отметки у них раздельные (как и сейчас для отметок).
- **ASSUMPTION — устаревшие записи.** После сброса `backend/data` запись в списке ведёт на экран ошибки анализа с текстом backend («Document not found») и ссылкой «Загрузить другой документ»; запись убирается вручную крестиком.
- **ASSUMPTION — современный браузер.** Наследование custom properties в `::backdrop` (Chrome ≥122, Safari ≥17.4, Firefox ≥120), `color-mix`, диапазон `font-weight: 300 700` в `@font-face`. В старом браузере фон backdrop будет прозрачным — косметика.
- **ASSUMPTION — шрифты и лицензия.** woff2 копируются без изменений (≈1,25 МБ бинарников в git); name-таблицы содержат copyright (Cormorant 4.002, Inter Tight 3.004, JetBrains Mono 2.305). Текст OFL 1.1 берётся из локального `/opt/homebrew/Cellar/rust/1.98.1/share/doc/rustc/licenses/OFL-1.1.txt` (канонический текст с переформатированными абзацами; начинается «SIL OPEN FONT LICENSE», «Version 1.1 - 26 February 2007», заканчивается «…OTHER DEALINGS IN THE FONT SOFTWARE.»). Reserved Font Names у этих семейств не заявлены; файлы не модифицируются.
- **ASSUMPTION — middleware.** Проверка Host/Origin пропускает `/fonts/*` для `localhost`/`127.0.0.1`; подтверждается `curl` в Ф1. `middleware.ts` не меняется.
- **UNKNOWN — предупреждение React 19 о `<script>`.** Скрипт рендерится серверным layout и при гидрации не пересоздаётся; если dev-консоль всё же покажет предупреждение, оно только dev и не влияет на тесты/сборку.
- **TOOLING.** В `frontend/` нет `node_modules` — нужен `npm ci`; `next build` может переписать `frontend/tsconfig.json` — этот churn не коммитится; ESLint `@next/next/no-head-element` не применяется к `app/`.
- **SCOPE — промежуточный вид.** После Ф1 экраны Ф2–Ф3 выглядят «перекрашенными legacy» (токены и шрифты верные, композиция старая) — допустимо; каждая фаза оставляет все страницы рабочими.
- **Параллельные группы не используются.** Ф2 и Ф3 пересекаются по `globals.css`, `design-tokens.test.ts`, `README.md`, а Ф3 потребляет `rememberDocument` из Ф2; все фазы последовательны.

## Phases

## Ф1: Фундамент «Бюро» — шрифты, токены, темы, иконки, ui-примитивы, оболочка

**Files in this phase:**

- Create: `frontend/public/fonts/CormorantGaramond-Light.woff2`, `CormorantGaramond-Regular.woff2`, `CormorantGaramond-Medium.woff2`, `CormorantGaramond-SemiBold.woff2`, `CormorantGaramond-Bold.woff2`, `InterTight-latin.woff2`, `InterTight-cyrillic.woff2`, `JetBrainsMono-Regular.woff2`, `JetBrainsMono-Medium.woff2`
- Create: `frontend/public/fonts/OFL.txt`
- Create: `frontend/lib/cn.ts`, `frontend/lib/theme.ts`
- Create: `frontend/components/icons/Ico.tsx`, `frontend/components/icons/Icon.tsx`
- Create: `frontend/components/ui/Button.tsx`, `Badge.tsx`, `Field.tsx`, `Input.tsx`, `Textarea.tsx`, `Skeleton.tsx`, `States.tsx`, `Notice.tsx`, `Dialog.tsx`, `PageHeader.tsx`, `ThemeToggle.tsx`
- Modify: `frontend/app/globals.css`, `frontend/tailwind.config.ts`, `frontend/app/layout.tsx`, `frontend/components/WorkspaceShell.tsx`, `README.md`
- Test: `frontend/__tests__/Theme.test.tsx`, `frontend/__tests__/ui.test.tsx`, `frontend/__tests__/WorkspaceShell.test.tsx`, `frontend/__tests__/design-tokens.test.ts`

**Interfaces:**
- Consumes: nothing
- Produces: `cn(...values: ClassValue[]): string`; theme API из C4 (`ThemeMode`, `ResolvedTheme`, `THEME_STORAGE_KEY = "disprot.theme"`, `readThemeMode`, `writeThemeMode`, `systemPrefersDark`, `resolveTheme`, `applyTheme`, `THEME_INIT_SCRIPT`); `Icon(props: IconProps)`, `IconName`, `Ico`, `IcoName` (C5); `Button`, `IconButton`, `buttonClassName`, `ButtonVariant`, `ButtonSize`, `Badge`, `Field`, `Input`, `Textarea`, `Skeleton`, `EmptyState`, `ErrorState`, `Notice`, `Dialog`, `PageHeader`, `ThemeToggle` с сигнатурами C6/C4; Tailwind-токены C3 (цвета `bg`/`ink`/`line-c`/`accent`/`warn`/`danger`/`ok`, `font-serif|sans|mono`, `rounded-xs…pill`, `shadow-sm|md`, `text-2xs`, `tracking-rubric`); CSS-классы `.rubric`, `.wrap-anywhere`, `.skip-link`; `WorkspaceShell` с неизменными props; `design-tokens.test.ts` с `LEGACY_TSX` (C14).

- [ ] **Step 1: Скопировать шрифты и оформить лицензию**

  `mkdir -p frontend/public/fonts && cp ../strigov-crm/apps/web/public/fonts/*.woff2 frontend/public/fonts/` (путь относительно корня репозитория: `/Users/strigov/Documents/Claude/Projects/projects-code/strigov-crm/apps/web/public/fonts/`); сверить `shasum -a 256` источника и копий. Создать `OFL.txt`: английская шапка с перечнем файлов и тремя строками copyright — «Copyright 2015 The Cormorant Project Authors (github.com/CatharsisFonts/Cormorant)», «Copyright 2022 The Inter Project Authors (https://github.com/rsms/inter-tight)», «Copyright 2020 The JetBrains Mono Project Authors (https://github.com/JetBrains/JetBrainsMono)» — затем дословно содержимое `/opt/homebrew/Cellar/rust/1.98.1/share/doc/rustc/licenses/OFL-1.1.txt`. Проверить, что `.gitignore` не исключает `frontend/public/` (проверено: не исключает).

- [ ] **Step 2: Написать падающие тесты темы и механической проверки**

  `Theme.test.tsx` по Test strategy Ф1 (стаб `window.matchMedia` через `vi.stubGlobal`/`Object.defineProperty` с `addEventListener`/`removeEventListener` и ручной отправкой `change`; `localStorage.clear()` в `beforeEach`; сброс атрибутов `<html>`). `design-tokens.test.ts` по C14 с allowlist Ф1 — сейчас падает на hex в `globals.css`.

- [ ] **Step 3: Токены, базовые правила и Tailwind**

  Переписать шапку `globals.css` по C2 (п. 1–4 и `.rubric`/`.wrap-anywhere`), `tailwind.config.ts` — по C3 (часть Ф1). Затем механически перекрасить оставшиеся legacy-классы по C13 до прохождения CSS-части `design-tokens.test.ts`; layout, размеры и breakpoints legacy-классов не менять. `.spinner` заменить на `motion-safe`-анимацию (правило reduced motion теперь содержит `animation-iteration-count: 1`).

- [ ] **Step 4: Тема до первой отрисовки**

  Реализовать `lib/theme.ts` (C4) без обращений к `window` на уровне модуля и с guard на `matchMedia`; `THEME_INIT_SCRIPT` собирать из `THEME_STORAGE_KEY`. Обновить `app/layout.tsx` ровно по C4 (атрибуты `<html>`, `suppressHydrationWarning`, `<head>` со скриптом, skip link).

- [ ] **Step 5: Иконки**

  `Ico.tsx` — шесть глифов с path-данными из `strigov-crm/apps/web/src/components/icons/Ico.tsx` (`size` деструктурируется и не попадает в `<svg>`). `Icon.tsx` — реестр C5 с явными именованными импортами из `lucide-react`, `strokeWidth={1.4}`, `absoluteStrokeWidth`, a11y-атрибуты по `label`.

- [ ] **Step 6: ui-примитивы**

  Сначала `ui.test.tsx` (Test strategy Ф1), затем `Button`, `Badge`, `Field`, `Input`, `Textarea`, `Skeleton`, `States`, `Notice`, `Dialog`, `PageHeader` строго по C6 (классы только токенами; `variant` обязателен; `forwardRef` с именованной функцией; `Dialog` переносит механику текущего `ExportDialog` — `showModal`-guard, `cancel`, восстановление фокуса).

- [ ] **Step 7: Переключатель темы и оболочка**

  `ThemeToggle` по C4; `WorkspaceShell` по C7 на `Icon`/токенах (удалить импорты lucide из оболочки; props и `navigate`-логику не менять). Написать `WorkspaceShell.test.tsx`. Удалить из `globals.css` правила `.brand*`, `.local-badge`, `.workflow*`, `.step-*`, `.workspace*`.

- [ ] **Step 8: README**

  В `README.md` добавить подраздел «Оформление»: дизайн-система «Бюро» (strigov-crm), переключатель темы в шапке и ключ `localStorage['disprot.theme']`, локальные шрифты в `frontend/public/fonts/` под SIL OFL 1.1 (`OFL.txt`), отсутствие внешних запросов.

- [ ] **Step 9: Проверка фазы**

  Общая проверка (Test strategy): lint, tsc, `npm test` (все прежние тесты без изменений + новые), `npm run build`, пустой diff `package.json`/`package-lock.json`/`middleware.ts`, откат churn `tsconfig.json`. `curl -sI http://127.0.0.1:3000/fonts/InterTight-cyrillic.woff2` → 200 и `font/woff2` (dev и `npm run start`). В браузере пройти все экраны в светлой и тёмной теме (включая «Как в системе» при смене темы ОС), убедиться в отсутствии вспышки при перезагрузке, видимом фокус-кольце, skip link и отсутствии внешних запросов в Network.

## Ф2: Входной поток — главная с недавними документами, анализ, стороны, экспорт

**Files in this phase:**

- Create: `frontend/lib/format.ts`, `frontend/lib/recent-documents.ts`, `frontend/components/RecentDocuments.tsx`
- Modify: `frontend/app/page.tsx`, `frontend/components/FileUpload.tsx`, `frontend/app/documents/[id]/analysis/page.tsx`, `frontend/app/documents/[id]/parties/page.tsx`, `frontend/components/PartySelector.tsx`, `frontend/components/AnalysisSummary.tsx`, `frontend/app/documents/[id]/export/page.tsx`, `frontend/components/ExportDialog.tsx`, `frontend/components/ExportForm.tsx`, `frontend/app/globals.css`, `README.md`
- Test: `frontend/__tests__/recent-documents.test.ts`, `frontend/__tests__/format.test.ts`, `frontend/__tests__/RecentDocuments.test.tsx` (новые); `frontend/__tests__/AnalysisPage.test.tsx`, `frontend/__tests__/PartiesPage.test.tsx`, `frontend/__tests__/FileUpload.test.tsx`, `frontend/__tests__/PartySelector.test.tsx`, `frontend/__tests__/design-tokens.test.ts` (изменения)

**Interfaces:**
- Consumes: из Ф1 — `Button`/`IconButton`/`buttonClassName` (`variant: "primary" | "ghost" | "outline" | "danger"`, `size?: "xs" | "sm" | "md"`), `Badge`, `Field({ label, required?, children })`, `Input`, `Skeleton({ className? })`, `EmptyState`, `ErrorState({ title?, titleLevel?, text?, onRetry?, retryLabel?, actions?, card?, className? })`, `Notice({ tone?, title?, children?, role?, id?, className? })`, `Dialog({ title, description?, onClose, dismissible?, closeLabel?, children, className? })`, `PageHeader({ rubric?, title, description?, meta?, actions? })`, `Icon({ name: IconName, size?, className?, label? })`, `cn`, `.rubric`, токены C3, `WorkspaceShell` (props без изменений)
- Produces: `fmtDateTime(value: number | Date, now?: Date): string`; `RecentStage`, `RecentDocument`, `RECENT_DOCUMENTS_KEY = "disprot.recent-documents"`, `RECENT_DOCUMENTS_LIMIT = 8`, `readRecentDocuments(): RecentDocument[]`, `rememberDocument(entry: { id: string; title?: string | null; stage: RecentStage }, now?: number): void`, `forgetDocument(id: string): void` (C8); `ExportDialog({ documentId, contractName?, rowCount, onClose })` с прежними props; `LEGACY_TSX` = `{ app/documents/[id]/protocol/page.tsx, components/ProtocolTable.tsx }`

- [ ] **Step 1: Библиотеки недавних документов и дат (TDD)**

  Написать `recent-documents.test.ts` и `format.test.ts` (Test strategy Ф2), затем `lib/recent-documents.ts` и `lib/format.ts` по C8. Никаких Tailwind-классов в `lib/` (Tailwind `content` не сканирует `lib/`).

- [ ] **Step 2: Главная**

  `RecentDocuments.test.tsx`, затем `components/RecentDocuments.tsx` по C8. `app/page.tsx` остаётся серверным компонентом: `PageHeader` (рубрика «От правок — к готовому документу», заголовок «Протокол разногласий. Каждая правка на своём месте.», прежнее описание), `FileUpload`, `RecentDocuments`, секция `h2` «Как это работает» (serif, с заглавной буквы) с тремя шагами: рубрики «01 / Документ», «02 / Стороны», «03 / Протокол», сетка `md:grid-cols-3`, ниже `md` — столбец.

- [ ] **Step 3: Загрузка файла**

  `FileUpload`: зона drop — `div` с `rounded-lg border border-dashed border-line-strong bg-bg-elev`, при перетаскивании `bg-accent-soft border-accent`; текст «Перетащите .docx сюда или выберите файл» остаётся прямым потомком этого `div`; иконка `file-up` (20px) или `loader-circle` с `motion-safe:animate-spin`; `<label>` с `buttonClassName({ variant: "primary" })` и `focus-within:outline focus-within:outline-2 focus-within:outline-accent focus-within:outline-offset-2` (сейчас фокус невидимого `input` не виден); ошибка — `Notice tone="danger" role="alert"`. После успешного `api.uploadDocument` и до `router.push` — `rememberDocument({ id: result.id, title: file.name.replace(/\.docx$/i, ""), stage: "analysis" })`. Добавить тест в `FileUpload.test.tsx`.

- [ ] **Step 4: Экран анализа**

  Сохранить `STATUS_MODE`, `modeOf`, polling и порядок вызовов без изменений. Добавить `attempt` в зависимости эффекта; `PageError` получает `retry: boolean` (`true` для ошибки запроса и неизвестного статуса, `false` для `failed`). Ошибка — `ErrorState titleLevel={1}` c `title`, `text=detail`, `onRetry` (сброс `error`/`analysis`, `attempt + 1`) при `retry`, и `actions` = `<Link className={buttonClassName({ variant: "ghost" })} href="/">Загрузить другой документ</Link>`. Ожидание: `PageHeader` с рубрикой «Анализ документа», в заголовке `<span role="status" aria-live="polite">` с прежними текстами, иконка `loader-circle` (`motion-safe:animate-spin text-accent`, `aria-hidden`) — это индикатор фонового процесса, а не загрузки блока данных, поэтому не Skeleton; «Продолжить» — `Button primary`. `rememberDocument` — по C8 (один раз, только для `poll`/`failed`/неизвестного статуса). Тесты по Test strategy Ф2.

- [ ] **Step 5: Экран сторон**

  Сохранить загрузку, двухпроходный PATCH, проверку существующего протокола и порядок вызовов. Разделить `loadError`/`submitError`; `attempt` в зависимостях эффекта загрузки. Загрузка: `Skeleton`-заглушки двух карточек и `<p>` «Загружаем…» (без «Стороны договора»). Ошибка загрузки: `ErrorState titleLevel={1}` «Не удалось загрузить стороны», `text` = сообщение, «Повторить». После загрузки: `PageHeader` (рубрика «Договор загружен», заголовок «Стороны договора», `meta` — название договора, прежнее описание), `AnalysisSummary`, `Notice tone="warn"` при отсутствии распознанных сторон, `PartySelector`, `Notice tone="danger" role="alert"` для `submitError`. Перечень условий: вычислить `blockers: string[]` в порядке — «Для протокола нужны две стороны. Добавьте недостающую или удалите лишнюю.» (если `parties.length !== 2`), «Заполните наименование и роль каждой стороны.» (если есть пустое имя/роль), «Отметьте вашу сторону — от её имени будет составлен протокол.» (если `!draftingUid`); при непустом списке рядом с кнопкой — `<div id="build-requirements">` с подписью «Чтобы построить протокол:» и `<ul>`; кнопка `Button primary` «Построить протокол» с `aria-describedby="build-requirements"` при наличии условий; прежний отдельный notice про две стороны удаляется (фраза переезжает в список). «Другой документ» — `Button ghost` с `arrow-left`. `rememberDocument({ id, title: a.contract_name, stage: "parties" })` после успешной загрузки. Тесты по Test strategy Ф2.

- [ ] **Step 6: Карточки сторон и сводка анализа**

  `PartySelector`: карточка `rounded-md border border-line-c bg-bg-elev p-4 shadow-sm`, выбранная — `outline outline-2 outline-accent -outline-offset-2`; радио с `accent-accent` и прежним `aria-label`; подпись выбора «Наша сторона»/«Сторона N» — `.rubric`; поля через `Field` + `Input` с прежними плейсхолдерами и `aria-label`; «Удалить» — `Button ghost size="xs"`; «Добавить сторону» — `Button ghost` с `plus` (обновить `PartySelector.test.tsx` по Test strategy); `fieldset disabled` и логика `remove`/`add` без изменений; сетка `md:grid-cols-2`. `AnalysisSummary`: полоса итогов — `Notice` (`warn` при замечаниях, иначе `ok`) с прежними текстами и `<strong>` для чисел; «Обратите внимание» — `Notice tone="warn"`; `<details>` «Подробности обработки документа» на токенах; `font-mono text-[10px]` → `font-mono text-2xs`; метрики — прямым текстом (C11).

- [ ] **Step 7: Экспорт**

  `ExportDialog` — на `Dialog` (`title="Скачать протокол"`, `dismissible={!busy}`), props не меняются. `ExportForm` — превью (`file-text` в `text-accent`, «Протокол разногласий», «Документ Word · .docx · Строк: N»), `Field` «Имя файла (без .docx)» + `Input` (прежние `aria-invalid`/`aria-describedby`), строка «Файл: ….docx» (`font-mono text-xs text-ink-2`), `Notice tone="danger" role="alert" id="export-error"`, `Notice tone="ok" role="status"`, `Button primary` на всю ширину с `download`/`loader-circle` и текстом «Сохранить»/«Сохраняем…» (иконки `aria-hidden`), подсказка «Все сохранённые изменения войдут в документ.». Страница `/export`: `PageHeader` (рубрика «Экспорт DOCX», заголовок «Экспорт», прежнее описание), ссылка «Вернуться к протоколу» через `buttonClassName({ variant: "ghost" })`, форма в карточке `rounded-md border border-line-c bg-bg-elev shadow-sm`.

- [ ] **Step 8: Очистка и README**

  Удалить из `globals.css` legacy-селекторы, у которых не осталось потребителей (`grep -rn "<класс>" app components` перед удалением). Сузить `LEGACY_TSX` до протокольных файлов. В `README.md` («Как пользоваться») описать недавние документы (хранятся в браузере, крестик убирает только из списка) и перечень условий на экране сторон.

- [ ] **Step 9: Проверка фазы**

  Общая проверка. В браузере в обеих темах и на ~375px: главная без и с недавними документами (включая удаление записи), загрузка неверного файла, анализ (ожидание, `samples/06_edge_broken.docx` → ошибка), ошибка сети анализа и сторон (остановить backend) → «Повторить» после запуска, стороны с выбором/без выбора стороны и пустыми полями, диалог и страница экспорта (Esc блокируется во время сохранения).

## Ф3: Рабочее пространство протокола на «Бюро» и разбиение ProtocolTable без изменения поведения

**Files in this phase:**

- Create: `frontend/components/protocol/types.ts`, `frontend/components/protocol/ProtocolToolbar.tsx`, `frontend/components/protocol/ClauseSidebar.tsx`, `frontend/components/protocol/ClauseFocusView.tsx`, `frontend/components/protocol/ProtocolGrid.tsx`
- Modify: `frontend/components/ProtocolTable.tsx`, `frontend/components/DiffText.tsx`, `frontend/app/documents/[id]/protocol/page.tsx`, `frontend/tailwind.config.ts`, `frontend/app/globals.css`
- Test: `frontend/__tests__/ProtocolPage.test.tsx`, `frontend/__tests__/design-tokens.test.ts`

**Interfaces:**
- Consumes: из Ф1 — `Button`, `IconButton`, `buttonClassName`, `Badge`, `Input`, `Textarea`, `Skeleton`, `EmptyState`, `ErrorState`, `Notice`, `PageHeader`, `Icon`, `cn`, `.rubric`, `.wrap-anywhere`, `WorkspaceShell`; из Ф2 — `rememberDocument(entry: { id: string; title?: string | null; stage: RecentStage }, now?: number): void`, `ExportDialog({ documentId, contractName?, rowCount, onClose })`
- Produces: `EditableField`, `ProtocolColumn`, `ClauseFilterValue`, `RenderCell` (C9, `components/protocol/types.ts`); `ProtocolToolbar`, `ClauseSidebar`, `ClauseFocusView`, `ProtocolGrid` с props C9 (`ProtocolGrid.renderActions`, `ClauseFocusView.actions` принимают готовый узел меню, поэтому Ф4 меняет только его реализацию); неизменный публичный API `ProtocolTable` (`ProtocolTableHandle`, `SaveState`, props); Tailwind-ключи `grid-cols-workbench`, `grid-cols-workbench-narrow`, `min-w-protocol-table`, `max-h-protocol-table`, `max-h-clause-list`, `max-h-clause-strip`; `design-tokens.test.ts` без `LEGACY_TSX` и с `ALLOWED_CSS_CLASSES` = `{ skip-link, rubric, wrap-anywhere, row-actions, row-menu, protocol-table }`

- [ ] **Step 1: Зафиксировать базовую линию**

  Запустить `npm test` и убедиться, что `ProtocolPage.test.tsx`, `ReviewRegressions.test.tsx`, `Workspace.test.tsx` зелёные; в этой фазе они не редактируются (кроме добавлений в `ProtocolPage.test.tsx`, Step 6).

- [ ] **Step 2: Вынести разметку из ProtocolTable**

  Создать `components/protocol/types.ts` и перенести туда `EditableField` (контейнер импортирует его оттуда). Вынести JSX в `ProtocolToolbar`, `ClauseSidebar`, `ClauseFocusView`, `ProtocolGrid` строго по C9; контейнер передаёт `renderCell = (row, field, label) => renderEditableText(row, field, label)`, `renderActions` (пока прежний `<details>`-блок, заменяется в Ф4), узлы `search`/`filter` (пока прежний `<select>` с `aria-label="Фильтр пунктов"`, перекрашенный токенами) и `empty`. Состояние, refs, `commit`, `saveAll`, `useImperativeHandle`, `beforeunload`, `changeView`, `toggleReviewed` не переносить и не менять. После шага — `npm test` зелёный.

- [ ] **Step 3: Оформление рабочей области**

  Добавить layout-ключи в `tailwind.config.ts` (C3, часть Ф3). Перевести контейнер и вынесенные компоненты на токены и примитивы: рабочая область `rounded-lg border border-line-c bg-bg-elev shadow-sm md:grid-cols-workbench-narrow lg:grid-cols-workbench`; сайдбар `bg-bg-sunk`, ниже `md` — горизонтальная лента пунктов `max-h-clause-strip` с карточками `w-40 shrink-0` (как текущее ≤700px), от `md` — список `max-h-clause-list`; активный пункт `bg-bg-active`; превью `line-clamp-2 wrap-anywhere text-xs text-ink-2`; заголовок пункта `font-serif text-2xl`; панели сравнения — рубрики «Контрагент»/«Наша сторона», шапка нашей панели `bg-accent-soft`, ниже `lg` панели в столбец; «Согласованная редакция» — `.rubric` + `rounded-md border border-line-strong bg-bg`; таблица по C9 (`sticky top-0` заголовки `bg-bg-sunk`, ячейки `align-top border-b border-line-c wrap-anywhere`). Редактируемый `span role="textbox"`: `block min-h-6 cursor-text whitespace-pre-wrap wrap-anywhere rounded-xs p-1 hover:bg-bg-hover focus-visible:bg-bg-hover`, blocked — `cursor-wait opacity-60`, пустой — `text-ink-2`; поля редактирования — `Input`/`Textarea` (для многострочных `min-h-36`), ошибка — `aria-invalid` + `<span role="alert" className="text-xs text-danger">`, «Сохраняем…» — `<span role="status" className="text-xs text-ink-2">`. Все тексты, `aria-*`, роли, обработчики клавиш (Enter/Space/F2, Esc, Ctrl/⌘+Enter) и `data-row-id`/`data-field` — без изменений. `DiffText`: `<del className="rounded-xs bg-danger-soft text-danger line-through">`, `<ins className="rounded-xs bg-ok-soft text-ok no-underline">`, логика без изменений. Временное меню строки (заменяется в Ф4) остаётся `<details className="row-actions">` с `<div className="row-menu">` и прежними кнопками, чтобы его позиционирование (включая `position: fixed` внутри таблицы) не менялось: `<table>` сохраняет класс-хук `protocol-table`, соответствующие legacy-правила остаются в `globals.css` (уже на токенах после Ф1); `summary` получает классы кнопки-иконки на токенах вместо `.icon-button`, а пункты меню — токенный цвет `text-danger` для «Исключить из протокола».

- [ ] **Step 4: Страница протокола**

  Сохранить эффект «список → существующий или build → затем анализ», `analysisVersion`, `refreshAnalysis`, `patch`, `perform`, `merge`, `remove`, `addRow`, `swap`, `onNavigate` через `perform`. Добавить `attempt` в зависимости эффекта загрузки и `ErrorState titleLevel={1}` «Не удалось загрузить протокол» с текстом ошибки и «Повторить» (сброс `error`, `attempt + 1`). Загрузка: `Skeleton` шапки и рабочей области (без `<table>`) + `<p>` «Строим таблицу…». Шапка: `PageHeader` (рубрика «Проверка протокола», заголовок «Протокол разногласий», `meta` — `file-text` + название договора, `.rubric` «Наша сторона» + имя, индикатор сохранения с `aria-live="polite"`: иконка `check` `text-ok` / `triangle-alert` `text-warn` / `circle-alert` `text-danger` / `loader-circle` `motion-safe:animate-spin`, текст `text-ink-1`), `actions` — `Button primary` `aria-label="Экспорт DOCX"` «Скачать DOCX». «Проверка полноты» — `<section aria-label="Проверка полноты">` в стиле `Notice` (`warn`/`ok`) с прежними текстами и кнопкой «Подробнее»/«Скрыть» (`aria-expanded`, `aria-controls="validation-details"`, текстовая кнопка `text-ink underline`); детали — `Notice tone="neutral"` с «Повторить проверку» (`Button ghost size="sm"`); `operationError` — `Notice tone="danger" role="alert"`. После первой успешной загрузки анализа в начальном эффекте — `rememberDocument({ id: params.id, title: a.contract_name, stage: "protocol" })` (не в `refreshAnalysis`).

- [ ] **Step 5: Удалить legacy CSS**

  Удалить из `globals.css` все оставшиеся legacy-классы, кроме правил временного меню строки (C2 п. 5); остальное содержимое — строго C2 (п. 1–4). Удалить `LEGACY_TSX` из `design-tokens.test.ts` и добавить проверку классовых селекторов `globals.css` с `ALLOWED_CSS_CLASSES` Ф3 (C14).

- [ ] **Step 6: Тесты страницы**

  Добавить в `ProtocolPage.test.tsx` два теста по Test strategy Ф3 (повтор без перестроения существующего протокола; запись в недавние). Остальные тесты не трогать.

- [ ] **Step 7: Проверка фазы**

  Общая проверка. В браузере на `samples/03_complex_styles_annex_tables.docx`: оба режима в обеих темах на ~1440/~1000/~375px (сайдбар-лента на узком экране, панели сравнения в столбец), редактирование ячеек мышью и клавиатурой (Enter/Space/F2, Esc, Ctrl/⌘+Enter), ошибка сохранения при остановленном backend и сохранение черновика, переключение режимов и экспорт во время сохранения, `beforeunload` при несохранённом черновике, липкие заголовки таблицы, видимость фокус-кольца внутри рабочей области.

## Ф4: UX проверки протокола — меню действий, подтверждение исключения, фильтр со счётчиками, «Проверено — дальше»

**Files in this phase:**

- Create: `frontend/components/protocol/RowActions.tsx`, `frontend/components/protocol/ClauseFilter.tsx`, `frontend/components/ui/ConfirmDialog.tsx`
- Modify: `frontend/components/ProtocolTable.tsx`, `frontend/components/protocol/ClauseSidebar.tsx`, `frontend/components/protocol/ClauseFocusView.tsx`, `frontend/components/protocol/ProtocolGrid.tsx`, `frontend/app/globals.css`, `README.md`
- Test: `frontend/__tests__/ProtocolActions.test.tsx` (новый); `frontend/__tests__/ProtocolPage.test.tsx`, `frontend/__tests__/ReviewRegressions.test.tsx`, `frontend/__tests__/Workspace.test.tsx` (намеренные изменения); `frontend/__tests__/design-tokens.test.ts` (финальный `ALLOWED_CSS_CLASSES`)

**Interfaces:**
- Consumes: из Ф1 — `Dialog({ title, description?, onClose, dismissible?, closeLabel?, children, className? })`, `Button`, `IconButton({ icon, label, size?, ...buttonAttrs })` с ref, `Badge({ tone? })`, `Icon`, `cn`; из Ф3 — `ClauseFilterValue`, `RenderCell`, `ClauseSidebar` (`filter: ReactNode`), `ClauseFocusView` (props C9), `ProtocolGrid` (`renderActions`, `filter`), контейнерные `changeView`, `toggleReviewed`, `filtered`, `activeIndex`, `isReviewed`, `saveState`, `rowHasPendingSave`; `ALLOWED_CSS_CLASSES` из `design-tokens.test.ts`
- Produces: nothing

- [ ] **Step 1: Тесты новых сценариев**

  Написать `ProtocolActions.test.tsx` по Test strategy Ф4 (рендер `ProtocolTable` напрямую, как в `Workspace.test.tsx`; `localStorage.clear()` в `beforeEach`; взаимодействия через `userEvent`, чтобы генерировались `pointerdown`).

- [ ] **Step 2: Меню действий строки**

  Реализовать `RowActions` по C10 и заменить `<details>` в `renderActions` контейнера: `disabled = busy || rowHasPendingSave(row.id)`, `onMergePrevious/onMergeNext` → `onMerge(row.id, "previous"|"next")`, `onRequestDelete` → `setPendingDelete(row)`. Координаты поповера — единственное место с inline `style` (вычисляемые значения, не токены). Удалить из `globals.css` правила временного меню (`.row-actions*`, `.row-menu*`, `.protocol-table .row-menu`), убрать класс-хук `protocol-table` с `<table>` и сузить `ALLOWED_CSS_CLASSES` в `design-tokens.test.ts` до `{ "skip-link", "rubric", "wrap-anywhere" }`.

- [ ] **Step 3: Подтверждение исключения**

  Реализовать `ConfirmDialog` по C10; в контейнере состояние `pendingDelete: ProtocolRow | null` и рендер диалога с копирайтом C10; подтверждение вызывает прежний `onDelete(id)`. Обновить тесты `ProtocolPage.test.tsx` и `ReviewRegressions.test.tsx` ровно по списку Test strategy Ф4.

- [ ] **Step 4: Фильтр со счётчиками**

  Реализовать `ClauseFilter` по C10, типизировать `filter` как `ClauseFilterValue`, вычислить `counts` (C10) и передать `<ClauseFilter layout="stack">` в `ClauseSidebar` и `<ClauseFilter layout="inline">` в `ProtocolGrid` вместо `<select>`; `revealRow` и «Сбросить фильтры» по-прежнему ставят `"all"`. Обновить `Workspace.test.tsx` по Test strategy Ф4.

- [ ] **Step 5: «Проверено — дальше»**

  Рефакторинг `toggleReviewed` в `setReviewMark` без изменения поведения чекбокса (C10), добавить `reviewAndNext`, новые props `ClauseFocusView` (`onReviewAndNext`, `reviewAndNextDisabled`) и кнопку в футере; строке позиции добавить `aria-live="polite"`. Прогнать тест «review marks survive remount…» из `Workspace.test.tsx` без изменений.

- [ ] **Step 6: README**

  Обновить шаги 5–7 «Как пользоваться»: счётчики фильтра, «Проверено — дальше» (отметка + переход; обычный «Следующий пункт» не ставит отметку), меню действий строки (Esc/клик вне) и подтверждение исключения без возможности отмены.

- [ ] **Step 7: Проверка фазы**

  Общая проверка; финальный `grep -rnE "text-(slate|gray|red|amber|emerald|blue)-" frontend/app frontend/components` пуст (дублирует `design-tokens.test.ts`). В браузере в обеих темах: меню в режиме «Таблица» у последних строк прокручиваемой таблицы (не обрезается, открывается вверх), закрытие по Esc/клику вне/прокрутке, клавиатура ↑/↓ в меню, исключение с отменой и подтверждением (фокус после закрытия диалога), фильтры и счётчики, «Проверено — дальше» на всём протоколе с фильтром «Не проверены мной», поведение при несохранённом черновике.
