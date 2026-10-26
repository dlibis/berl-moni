# Workstream B — Names, table filters, flags, decision

## 1. Goal

Align the primary requests table (Pniyot / פניות) with spec §3: rename user-facing terminology away from מכתבים, reshape filters and row labels to match the §3.2 matrix, hide internal queue state (`בתור`) from the UI, widen **Unanalyzed** to cover `discovered`/`queued`/`analyzing`, drop **Sent** and **Old Version** filters (mail send unchanged), add manual **דורש עיון** and persisted **Passed / Not Passed** (`עברה` / `לא עברה`, default false), rename **Failed** to **Error** (`תקלה`) in the UI, and keep auto **דורשים ניתוח**.

**Spec source:** `Berl Katznelson Monitor - Agent System Specification.md` §3 (read from repo; not present in this worktree root — only `docs/PRD-extraction-and-relevance.md` is checked in here).

## 2. Current code (files, functions, what exists)

| Area | Location | Behavior today |
|------|----------|----------------|
| Table filters (UI) | `client/src/features/letters/status-filter.tsx` | Options: `not_analyzed`, `queued`, `relevant`, `irrelevant`, `failed`, `sent`, `needs_analysis`, `outdated`; all-items label **כל המכתבים**. |
| Filter types | `client/src/features/letters/types.ts` | `LetterStatusFilter` union matches the eight keys above; `LetterItem` has derived `needs_analysis`, `outdated`, no `requires_review` or `passed`. |
| Row badge | `client/src/features/letters/letter-status-badge.tsx` | Shows **בתור**, **בניתוח**, **נכשל**, **גרסה ישנה**, **דרוש ניתוח** (singular), **רלוונטי** / **לא רלוונטי** by `analysis_status` + flags. |
| List API filters | `web/views/letters.py` → `FILTERS`, `list_letters()`, `_item()` | `not_analyzed` = only `discovered`; `queued` = `queued`/`analyzing`; `sent` = `send_count > 0`; `outdated` = SQL prefetch + `is_outdated()` in Python; `needs_analysis` = relevant ∧ incomplete; `failed` = `analysis_status = 'failed'`. |
| Route validation | `web/routes/letters.py` → `get_letters()` | Rejects unknown `status` unless key ∈ `FILTERS`. |
| DB queue state | `db/migrations/005_letters_page.sql` | `analysis_status` CHECK: `discovered`, `queued`, `analyzing`, `analyzed`, `failed` — worker queue; no `requires_review` / `passed`. |
| Polling while queued | `client/src/hooks/use-letters.ts` | Refetches every 5s when any visible row has `queued`/`analyzing` (keep; queue still exists). |
| Terminology (מכתב) | Multiple under `client/src/` (see grep) | Table empty states, refresh button, status filter “all”, letter detail fallback title, toasts, letter-actions tooltips, etc. |
| Tests | `tests/test_letters_api.py` | `test_derived_flags_and_outdated_filter` asserts `outdated` and `needs_analysis` filters; no `sent`/`queued` filter tests. |

Sending mail: `POST /api/v1/letters/<slug>/send` in `web/routes/letters.py` — unchanged by this workstream except filter removal.

## 3. Functional requirements

**FR-WB-1 — Pniyot terminology (§3.1)**  
All **user-facing** strings that refer to the ingested entity as a “letter” (מכתב/מכתבים) in the requests table flow must say **פנייה/פניות** (or neutral “בקשה” where grammar requires singular), including: status filter “all” label, table empty states, refresh control, letter list hooks toasts tied to ingest, letter detail fallback title, and letter-actions send/analyze blockers.  
**Acceptance:** No remaining `מכתב` in `client/src/features/letters/**`, `client/src/pages/home.tsx`, `client/src/pages/letter.tsx`, and the hooks that only serve the letters table (`use-refresh-letters`, `use-analyze-letter`, `use-send-letter` for user-visible strings). Report copy that quotes PDF wording (e.g. “מכתב סרוק”) may stay.

**FR-WB-2 — Filter set matches §3.2**  
The status dropdown exposes exactly these filters (plus “all”): **לא נותחו**, **תקלה**, **דורש עיון**, **דורשים ניתוח**, **רלוונטי**, **לא רלוונטי**. Labels for relevant/not relevant use spec singular forms in the filter list (not “רלוונטיים”).  
**Acceptance:** `status-filter.tsx` and `LetterStatusFilter` contain no `queued`, `sent`, or `outdated` keys; “all” reads **כל הפניות**.

**FR-WB-3 — Remove Sent and Old Version filters (§3.2 “Not in the table”)**  
**Acceptance:** `FILTERS` has no `sent` or `outdated`; `GET /api/v1/letters?status=sent|outdated` → 400; client cannot select them. `send_count` / `last_sent_at` columns and send API still work.

**FR-WB-4 — Hide בתור from table UI (§3.2)**  
No filter and no badge text **בתור** or **בניתוח**. Internal `analysis_status` values unchanged.  
**Acceptance:** `letter-status-badge.tsx` never renders queue/processing labels; `status-filter.tsx` has no `queued` option.

**FR-WB-5 — Unanalyzed aggregates internal states (§3.2)**  
Filter **לא נותחו** (`not_analyzed`) matches `analysis_status IN ('discovered','queued','analyzing')`.  
**Acceptance:** Seeded rows in `queued`/`analyzing` appear under `?status=not_analyzed` and show the same user-facing unanalyzed label as `discovered` (spec: user-facing “Unanalyzed”).

**FR-WB-6 — Error label replaces Failed (§3.2)**  
User-facing label for `analysis_status = 'failed'` is **תקלה** (not **נכשל** / **נכשלו**). Filter name in dropdown is **תקלה**.  
**Acceptance:** Badge and filter use **תקלה**; optional API key rename `failed` → `error` is allowed if client and `FILTERS` stay in sync (if key stays `failed`, Hebrew label still must be **תקלה**).

**FR-WB-7 — Manual דורש עיון (§3.2)**  
Persist a boolean on each letter, default `false`, set only via explicit user action (never analysis pipeline).  
**Storage:** one column on `letters`, e.g. `requires_review boolean NOT NULL DEFAULT false` (new migration after `005_letters_page.sql`).  
**Acceptance:** Column exists; list/detail JSON includes `requires_review`; pipeline code paths do not write it; user can set/clear it (e.g. `PATCH /api/v1/letters/<slug>` body `{ "requires_review": true|false }` or dedicated sub-route); filter **דורש עיון** returns rows where `requires_review IS TRUE`; badge or secondary chip shows **דורש עיון** when true, independent of `needs_analysis` and relevance.

**FR-WB-8 — Keep auto דורשים ניתוח (§3.2)**  
Derived rule unchanged: relevant ∧ incomplete extraction → `needs_analysis` in `_item()`. Filter key `needs_analysis`, label **דורשים ניתוח**. Badge text aligned to **דורשים ניתוח** (not “דרוש ניתוח”).  
**Acceptance:** Existing `test_derived_flags_and_outdated_filter` needs_analysis assertion still passes after removing outdated parts; auto flag cannot be toggled manually via the same control as `requires_review`.

**FR-WB-9 — Relevant / Not Relevant row labels (§3.2)**  
For analyzed, non-error rows without higher-priority flags, badge shows **רלוונטי** or **לא רלוונטי** per existing `relevant` SQL in `web/views/letters.py`.  
**Acceptance:** No **גרסה ישנה** badge (outdated remains computable for other workstreams if needed, but not shown per §3.2).

**FR-WB-10 — Passed / Not Passed decision status (§3.3)**  
Independent boolean on `letters`, default `false` (**לא עברה**). User can mark **עברה** (`true`). New ingest rows default to not passed.  
**Storage:** one column, e.g. `passed boolean NOT NULL DEFAULT false` in the same migration as FR-WB-7.  
**Acceptance:** Exposed on list/detail API; visible on table and/or detail with clear **עברה** / **לא עברה**; toggled only by user action; not implied by `analysis_status` or relevance.

**FR-WB-11 — List API contract**  
`COLUMNS` / `_item()` in `web/views/letters.py` return `requires_review` and `passed`; `FILTERS` updated per FR-WB-2–WB-8. Remove `list_letters` special-case branch for `outdated` (no longer a filter).  
**Acceptance:** `tests/test_letters_api.py` updated: drop outdated filter expectations; add cases for expanded `not_analyzed`, `requires_review` filter, and invalid removed statuses.

## 4. Files to change (repo-relative paths)

| Path | Change |
|------|--------|
| `db/migrations/006_<name>.sql` (new) | `requires_review`, `passed` on `letters`. |
| `web/views/letters.py` | `FILTERS`, `COLUMNS`, `_item()`, remove `outdated` list branch. |
| `web/routes/letters.py` | Validate new filter keys; add PATCH (or equivalent) for manual flags. |
| `client/src/features/letters/types.ts` | Filter union, `LetterItem` fields. |
| `client/src/features/letters/status-filter.tsx` | Options + **כל הפניות**. |
| `client/src/features/letters/letter-status-badge.tsx` | Label matrix per §3.2. |
| `client/src/features/letters/letters-table.tsx` | Empty-state copy; optional **עברה/לא עברה** column. |
| `client/src/features/letters/letter-row.tsx` / `letter-card.tsx` | Decision + review UI if not only on detail. |
| `client/src/features/letters/letter-actions.tsx` (or new control) | Toggle `requires_review` / `passed`. |
| `client/src/pages/letter.tsx`, `client/src/pages/home.tsx` | Pniyot copy. |
| `client/src/hooks/use-*.ts` (letters-related toasts) | Pniyot copy per FR-WB-1. |
| `tests/test_letters_api.py` | Filters, flags, PATCH, migration defaults. |
| Optional: `bot/adapters/postgres/letters.py` | Only if INSERT paths must explicitly set new columns (defaults should suffice). |

Add spec file to worktree if orchestrator expects it at root (not required for implementation if agents read parent repo).

## 5. Tests to add/update

1. **`tests/test_letters_api.py`**  
   - Update `test_derived_flags_and_outdated_filter`: remove `outdated` filter assertions; keep `needs_analysis`.  
   - Add: `queued`/`analyzing` rows included in `status=not_analyzed`.  
   - Add: `status=sent|outdated|queued` → 400.  
   - Add: `requires_review` filter + PATCH toggle; pipeline analyze does not set `requires_review`.  
   - Add: new row / insert → `passed === false`; PATCH sets `passed true`.

2. **Migration test** (follow `tests/test_migration_005.py` pattern if present): new columns default false.

3. **Client** (optional, if project has frontend tests): snapshot or unit test for filter option list — only if repo already tests React components (none found in quick scan; skip unless added elsewhere).

## 6. Out of scope for this workstream

- Relevance rules (§2), provenance field names, coalition/master logic.  
- Excel export, notifications, master xlsx (§4).  
- Renaming REST paths (`/api/v1/letters`) or DB table name `letters`.  
- Error retry, LLM-unavailable, Always Send overlap, OCR near-miss on §2 strings.  
- Changing worker queue semantics or `analysis_status` enum values.  
- Email/PDF bot copy in `bot/service_layer/services.py` and summary PDF renderer (unless explicitly pulled into FR-WB-1 later).  
- `outdated` computation removal from `_item()` — only user-visible filter/badge removal; derived `outdated` in JSON may remain for other agents unless product asks to drop it entirely.

## 7. Resume

If this job stopped mid-rate-limit: re-read spec §3 from `Berl Katznelson Monitor - Agent System Specification.md` (parent `berl-moni` repo if missing in worktree). Implementation hinges on `web/views/letters.py` `FILTERS`/`list_letters` and `client/src/features/letters/status-filter.tsx` + `letter-status-badge.tsx`. Add migration `requires_review` + `passed` on `letters` before API/UI. Do not redo relevance or send pipeline work. Remove only **filters** for sent/outdated/queued and **UI** for בתור; keep `analysis_status` queue. Update `tests/test_letters_api.py` last as the contract check. Copy spec into worktree if your harness requires a local path.

---

## Agent notes (verification)

- Read spec §3 from `/Users/dafna/Documents/berl-moni/Berl Katznelson Monitor - Agent System Specification.md` (lines 28–61).
- Opened and cross-checked: `status-filter.tsx`, `letter-status-badge.tsx`, `types.ts`, `web/views/letters.py`, `web/routes/letters.py`, `005_letters_page.sql`, `tests/test_letters_api.py` (`test_derived_flags_and_outdated_filter`), `use-letters.ts`, `letters-table.tsx`, client `מכתב` grep.
- Confirmed spec file is **not** in worktree root (only `docs/PRD-extraction-and-relevance.md`).

### OPEN ITEMS

- Spec file should be added or linked in the worktree so delegated agents do not rely on parent path.
- Whether API filter key `failed` is renamed to `error` (Hebrew **תקלה** is required either way).
- Exact UX for toggling `requires_review` and `passed` (table vs detail only) — spec mandates behavior, not layout.
- Whether list JSON should stop emitting `outdated` once badges drop it (left as implementer choice in §6).
