# Workstream C — Excel export, program master, notifications

## 1. Goal

Implement spec **§4** in berl-moni: one-click Excel export of the primary Pniyot table (with a hyperlink to each row’s Knesset PDF), `.xlsx` upload/download for the 6-digit master program list, mailing subscribers with required **Email** and **Name**, and **Always Send** (`שלח תמיד`) as a **weekly** cron that runs **in parallel** with existing custom date-range schedules. Sending mail itself stays as today; this workstream does not change relevance, table filters, or the Pniyot rename (other workstreams).

**Source of truth:** `Berl Katznelson Monitor - Agent System Specification.md` §4 (read from repo parent: `/Users/dafna/Documents/berl-moni/Berl Katznelson Monitor - Agent System Specification.md`; not present in this worktree). **Do not** define Always Send vs custom-range overlap (spec “Not specified here”).

---

## 2. Current code (files, functions, what exists)

### Excel export
- **None.** Home (`client/src/pages/home.tsx`) has filter + refresh only; no export control.
- Table data: `GET /api/v1/letters` → `web/routes/letters.py` → `web/views/letters.py` (`list_letters`, `COLUMNS`, `FILTERS`, `_item`).
- Row fields exposed today include `letter_url` (Knesset PDF URL), `letter_date`, `ministry`, `request_numbers`, `relevant`, `complete`, `needs_analysis`, `analysis_status`, `last_sent_at`, `send_count`, etc.

### Program master
- **DB:** `programs` (`code` 6-digit PK, `name`) — `db/migrations/001_init.sql`.
- **API:** CRUD JSON only — `web/routes/master.py` (`get_master`, `add_program`, `update_program`, `delete_program`); codes `^[0-9]{1,6}$` zero-padded to 6.
- **Load path:** `common/db.py` `load_programs()`; bot/tests use Neon, not runtime xlsx (`bot/tests/test_master_programs.py`).
- **UI:** `client/src/pages/programs.tsx` + `client/src/features/programs/*` — inline add/edit/delete via `/api/v1/master`; **no** upload/download.
- **Legacy / local:** `files/.gitkeep` mentions `master.xlsx`; `openpyxl`/`pandas` in **bot** dependency group only (`pyproject.toml`); `common/db.py` docstring: web routes avoid pandas. `tests/test_web_bundle.py` blocks pandas on the Vercel import path.
- **Format reference (not §4):** `docs/PRD-extraction-and-relevance.md` — sheet `תוכניות`, columns `קוד`, `שם תוכנית`, 6-digit normalization (use for xlsx shape unless product says otherwise).

`docs/cloud-mailbox-plan.md` (parent repo) lists runtime Excel upload as **dropped**; **§4 overrides** for this workstream.

### Notifications (subscribers + dispatch)
- **Mailing list DB:** `mailing_list` — **email only** (`db/migrations/001_init.sql`).
- **API:** `web/routes/mailing_list.py` — GET list + cap; POST/DELETE by `email` only; `list_emails` / `add_email` / `remove_email` in `common/db.py`.
- **UI:** `client/src/features/mailing-list/*` — email-only forms and table (`email-form.tsx`, `recipient-list.tsx`).
- **Mailbox (sender):** `web/routes/notifier.py` — `from_address`, `reply_to_address` (not subscribers).
- **Auto send pipeline:** `bot/service_layer/services.py` `send_job` — `uow.due_day(now)` gate; recipients from `uow.mailing_list()` minus reply-to; uses `settings.schedule` + `auto_since`.
- **Schedule due:** `common/schedule_due.py` — `due_day`, `day_time`, `schedule_configured`; one **auto** run per Israel **day** (`send_runs_one_auto_per_day` in `db/migrations/005_letters_page.sql`).
- **Cron:** `.github/workflows/letters.yml` — **hourly** `0 * * * *`; `common/schedule_due.py` main → `due` / `queued` → `bot.entrypoints.main` (drain + `send_job`).
- **Schedule UI/API:** `web/routes/schedule.py`, `client/src/features/schedule/*` — date ranges + weekday/hour slots; **no** Always Send toggle.
- **No** `שלח תמיד` / `always_send` in codebase (grep).

---

## 3. Functional requirements

### Excel export

**FR-WC-1 — One-click export**  
- **Requirement:** Authenticated user can export the **primary Pniyot table** in one action from the main table view (Home).  
- **Acceptance:** A visible control on Home triggers download of a single `.xlsx` file without paginating manually; unauthenticated requests are rejected (same session model as other `/api/v1/*` routes).

**FR-WC-2 — Spreadsheet content and PDF link**  
- **Requirement:** Export includes the same logical rows as the primary table dataset (all ingested Pniyot, not only the current page). Each row includes a **hyperlink** to the original Knesset PDF (`letter_url` from `web/views/letters.py`).  
- **Acceptance:** Opening the file in Excel/LibreOffice shows at least one cell per row as a clickable URL to `letter_url`; row count matches DB row count for `letters` (or the filtered “All Requests” set once workstream B aligns filters). Column set follows **§3.2–3.3** table semantics when available; until then, minimum columns matching current UI: date, request numbers, ministry, status-related fields derived from `list_letters` / `_item`, plus PDF link.

**FR-WC-3 — Server-side generation without breaking the web bundle**  
- **Requirement:** Generate `.xlsx` on the server (hyperlinks need a real xlsx library). Do **not** import pandas in the Vercel web bundle (`tests/test_web_bundle.py`).  
- **Acceptance:** `openpyxl` (or equivalent) used from web layer with dependency added to **main** `project.dependencies` if needed; `test_web_app_and_render_need_no_bot_only_packages` still passes; export route does not import bot-only adapters.

### Program master (xlsx)

**FR-WC-4 — Download master list**  
- **Requirement:** Authenticated download of the **active** 6-digit master program list as `.xlsx`.  
- **Acceptance:** `GET` (or dedicated export endpoint) returns `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`; every `programs` row appears with 6-digit `code` and `name`; sheet/column layout compatible with upload (FR-WC-5), aligned with `תוכניות` / `קוד` / `שם תוכנית` per extraction PRD appendix unless §4 is extended.

**FR-WC-5 — Upload master list**  
- **Requirement:** Authenticated upload of `.xlsx` replaces/syncs the active master in `programs` (6-digit codes).  
- **Acceptance:** Valid file updates `programs` so subsequent `load_programs()` and `GET /api/v1/master` match file contents; invalid file (wrong sheet/columns, non-numeric codes, duplicates) returns 4xx with no partial destructive apply (transactional replace or explicit merge policy documented in implementation — default: **full replace** of `programs` from file rows). Re-upload is idempotent for the same file.

**FR-WC-6 — Programs UI**  
- **Requirement:** Programs page exposes **Download** and **Upload** in addition to existing CRUD (or CRUD remains for single-row edits; bulk path is xlsx).  
- **Acceptance:** User can download and re-upload without CLI/`seed_programs.py`; gitignored local seed script remains optional for ops, not required for product flow.

**FR-WC-7 — Master resync vs bypass relevance**  
- **Requirement:** This workstream only maintains the `programs` table; it does **not** implement §2 provenance/freeze (other workstream).  
- **Acceptance:** Upload/download tests assert `programs` contents only; no claim that upload changes Relevant on bypass-frozen rows.

### Notifications (subscribers)

**FR-WC-8 — Subscriber schema**  
- **Requirement:** Subscribers have **required** `Email` (string) and **Name** (string) per §4.  
- **Acceptance:** DB migration adds `name` (NOT NULL for new rows; migration strategy for existing email-only rows documented — e.g. backfill placeholder disallowed for new adds); API rejects create/update without non-empty trimmed `name` and valid email.

**FR-WC-9 — Subscriber API and UI**  
- **Requirement:** Mailing list CRUD uses `{ email, name }`; list displays both fields.  
- **Acceptance:** `GET /api/v1/mailing_list` returns subscribers with `name`; POST requires both; edit flow preserves both; cap logic in `web/routes/mailing_list.py` unchanged in spirit (`list_cap`, advisory lock). `send_job` continues to send to email addresses; **Name** is stored for display/UI (and future email personalization only if spec adds it later).

### Always Send (`שלח תמיד`)

**FR-WC-10 — Setting and UI**  
- **Requirement:** Operators can enable **Always Send** (`שלח תמיד`) independently of custom date-range schedule.  
- **Acceptance:** Persisted setting (e.g. `settings` jsonb key); Schedule page (or adjacent notifications UI) shows Hebrew label `שלח תמיד` and toggle; GET/POST schedule or dedicated settings endpoint exposes state to the client.

**FR-WC-11 — Weekly cron**  
- **Requirement:** When Always Send is enabled, a **weekly** cron triggers the send pipeline **in parallel** with custom range schedules (§4).  
- **Acceptance:** New or extended GitHub Actions workflow with `schedule` cron at weekly granularity (specific weekday/time chosen in implementation and documented for operators); workflow runs the same worker entrypoint as `letters.yml` when Always Send is due; disabled toggle causes weekly job to no-op without affecting hourly schedule checks.

**FR-WC-12 — Custom schedules unchanged**  
- **Requirement:** Existing hourly `letters.yml` + `due_day(schedule, …)` behavior remains for custom date-range schedules.  
- **Acceptance:** `tests/test_schedule_due.py` and `tests/test_schedule_route.py` continue to pass; custom schedule still drives `due_day` when ranges/slots match.

**FR-WC-13 — Overlap unspecified**  
- **Requirement:** Do **not** invent rules when weekly Always Send and a custom slot fall on the same calendar day.  
- **Acceptance:** PRD/implementation notes reference spec “Not specified here”; no silent spec invented in code comments as product law. Document actual behavior chosen at implement time for orchestrator review (e.g. interaction with `send_runs_one_auto_per_day`).

---

## 4. Files to change (repo-relative paths)

| Area | Paths |
|------|--------|
| Export API + view | `web/routes/letters.py` (or new `web/routes/export.py`), `web/views/letters.py` (shared row builder), `web/routes/__init__.py` |
| Export UI | `client/src/pages/home.tsx`, new hook/button under `client/src/features/letters/` |
| Master xlsx | `web/routes/master.py` (upload/download handlers), optional `web/master_xlsx.py` helper |
| Master UI | `client/src/pages/programs.tsx`, `client/src/features/programs/*` |
| Subscribers DB | `db/migrations/006_mailing_list_name.sql` (new) |
| Subscribers API | `web/routes/mailing_list.py`, `common/db.py` |
| Subscribers UI | `client/src/features/mailing-list/*`, `client/src/hooks/use-mailing-list.ts` |
| Always Send | `db/migrations/006_…` or `002`-style seed for `always_send`; `web/routes/schedule.py`; `client/src/features/schedule/*`; `common/schedule_due.py` and/or new `common/always_send_due.py`; `bot/service_layer/services.py` + UoW `due_day` wiring; `.github/workflows/` (new weekly workflow or extend `letters.yml`) |
| Dependencies | `pyproject.toml` (add `openpyxl` to web deps if not already in main) |
| Tests | See §5 |

---

## 5. Tests to add/update

| Test file | Coverage |
|-----------|----------|
| `tests/test_letters_export.py` (new) | Export auth, xlsx content type, row count, hyperlink on `letter_url` |
| `tests/test_master_xlsx.py` (new) | Round-trip upload/download; invalid file 400; 6-digit normalization |
| `tests/test_web_db.py` or `tests/test_mailing_list.py` (new) | POST without `name` → 400; GET returns names |
| `tests/test_schedule_due.py` | Extend only if `due_day` / always-send helper changes |
| `tests/test_web_bundle.py` | Re-run after adding openpyxl to web — still no pandas |
| `bot/tests/test_main_cli.py` / send integration | If `send_job` gains always-send entry, smoke that recipients still resolve |

Update client only if e2e exists; otherwise API tests are sufficient per repo style.

---

## 6. Out of scope for this workstream

- Relevance rules, provenance freeze, §2 bypass (workstream A/B).
- Table filter taxonomy, `לא נותחו` / drop Sent & Old Version filters, `דורש עיון`, Passed/Not Passed columns (workstream B).
- Pniyot rename in UI copy and routes (workstream B); mention **Pniyot** only where naming exports.
- Error retry, LLM-unavailable, OCR near-miss, provenance column names.
- Inventing Always Send vs custom-range overlap or extra subscriber fields.
- Replacing Resend, cron host, or mailbox `from`/`reply-to` semantics (`notifier.py`).
- Importing new product rules from `docs/cloud-mailbox-plan.md` beyond factual “today’s architecture” notes.

---

## 7. Resume

If this job stopped mid-rate-limit: re-read **§4** in `Berl Katznelson Monitor - Agent System Specification.md` (parent dir of worktree). In the worktree, confirm no export/always-send landed yet via grep (`export`, `always_send`, `שלח תמיד`, `openpyxl` in `web/`). Core touchpoints: `web/views/letters.py` + Home UI (export); `web/routes/master.py` + Programs UI (xlsx); `mailing_list` migration + `web/routes/mailing_list.py` (email+name); `common/schedule_due.py`, `bot/service_layer/services.py` `send_job`, `.github/workflows/letters.yml` (hourly) plus **new weekly** workflow for Always Send. Do **not** redo full relevance/table PRDs. Keep web bundle free of pandas. Do **not** specify overlap between weekly Always Send and custom slots. `cloud-mailbox-plan.md` is historical for Excel upload being dropped—**ignore** that for §4 delivery.

---

### VERIFICATION

- Read spec §4 and “Not specified here” from `/Users/dafna/Documents/berl-moni/Berl Katznelson Monitor - Agent System Specification.md`.
- Opened: `web/routes/master.py`, `mailing_list.py`, `schedule.py`, `notifier.py`, `letters.py`, `web/views/letters.py`, `common/db.py`, `common/schedule_due.py`, `common/limits.py`, `bot/service_layer/services.py` (`send_job`), `bot/entrypoints/main.py`, `db/migrations/001_init.sql`, `005_letters_page.sql`, `002_seed_settings.sql`, `.github/workflows/letters.yml`, Home/Programs/Mailing/Schedule client pages, `pyproject.toml`, `tests/test_web_bundle.py`.
- Grep: no `always_send` / `שלח תמיד` / export routes in worktree; `mailing_list` email-only; hourly cron only.
- Skipped `docs/cloud-mailbox-plan.md` for product rules except noting conflict with §4 on xlsx upload.

### OPEN ITEMS

- Spec file not in worktree (only parent path)—copy into repo if agents must not leave worktree.
- **FR-WC-13:** Same-day weekly Always Send vs custom `due_day` vs `send_runs_one_auto_per_day` needs an explicit product decision; spec forbids inventing it here.
- Export column list final binding to post–workstream-B table columns should be reconciled when B lands.
- Whether `Name` affects Resend payload is unspecified in §4; store + UI only unless spec extends.

## Agent notes (verification)

- Read spec §4 and “Not specified here” from `/Users/dafna/Documents/berl-moni/Berl Katznelson Monitor - Agent System Specification.md`.
- Opened: `web/routes/master.py`, `mailing_list.py`, `schedule.py`, `notifier.py`, `letters.py`, `web/views/letters.py`, `common/db.py`, `common/schedule_due.py`, `common/limits.py`, `bot/service_layer/services.py` (`send_job`), `bot/entrypoints/main.py`, `db/migrations/001_init.sql`, `005_letters_page.sql`, `002_seed_settings.sql`, `.github/workflows/letters.yml`, Home/Programs/Mailing/Schedule client pages, `pyproject.toml`, `tests/test_web_bundle.py`.
- Grep: no `always_send` / `שלח תמיד` / export routes in worktree; `mailing_list` email-only; hourly cron only.
- Skipped `docs/cloud-mailbox-plan.md` for product rules except noting conflict with §4 on xlsx upload.

### OPEN ITEMS

- Spec file not in worktree (only parent path)—copy into repo if agents must not leave worktree.
- **FR-WC-13:** Same-day weekly Always Send vs custom `due_day` vs `send_runs_one_auto_per_day` needs an explicit product decision; spec forbids inventing it here.
- Export column list final binding to post–workstream-B table columns should be reconciled when B lands.
- Whether `Name` affects Resend payload is unspecified in §4; store + UI only unless spec extends.
