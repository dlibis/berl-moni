# Workstream A — Relevance, classification, provenance (PRD slice)

## 1. Goal

Implement spec **§2 Relevance** and **§2.1 Provenance** on top of the existing extraction pipeline: a Pniya is **Relevant** when any of three paths applies; after a **complete** scan with none of them, it is **Not Relevant**; **Error** (`analysis_status = 'failed'` with no usable classification) is never Not Relevant. Persist bypass provenance on the extraction payload so master-list resync cannot demote (1)/(2) letters. Centralize the relevance predicate so worker, SQL list filters, auto-send, and manual send stay consistent.

## 2. Current code (files, functions, what exists)

| Location | What it does today |
|---|---|
| `Berl Katznelson Monitor - Agent System Specification.md` §2–§2.1 | Target rules (read from repo root `dlibis/berl-moni`; not copied into this worktree). |
| `docs/PRD-extraction-and-relevance.md` | Approved extraction PRD: relevance = **only** master table-code match (FR-5/FR-6); `coalition_funds` is LLM-only for the field, not a relevance gate. |
| `bot/domain/extraction.py` | `Extraction.codes()`, `matched()`, `relevant_to(programs)` → **path (3) only** (`bool(codes ∩ programs)`). `Extractor.extract()`: parses table → if **not** `relevant_to(self.master)` → returns early with `fields=None` (**no LLM**). Otherwise runs LLM and full fields. `complete` = `fields is not None`. |
| `bot/adapters/postgres/letters.py` | `finish_analysis` → `analysis_status='analyzed'`, stores `extraction` JSON + `codes` (table codes only). `fail_analysis` → `'failed'` if no prior extraction, else stays `'analyzed'`. `auto_eligible` → `codes && ARRAY(SELECT code FROM programs)` plus `fields` object. |
| `bot/service_layer/analysis.py` | `drain_queue`: extract → `finish_analysis` / `fail_analysis`. `request_analysis`: “done” when saved extraction is `complete` **or** `not relevant_to(programs)` (master-only). |
| `web/views/letters.py` | `RELEVANT = coalesce(codes && programs, false)`; `COMPLETE` = `fields` object in JSON; `needs_analysis` = relevant ∧ ¬complete. Filters `relevant` / `irrelevant` / `needs_analysis` use `RELEVANT`. |
| `bot/service_layer/sending.py` | Send allowed only if `extraction.complete` **and** `relevant_to(programs)`. |
| `common/db.py` | `load_programs` → active master list from `programs` table. |
| `bot/tests/test_analysis_queue.py` | `test_newly_relevant_letter_needs_llm`: after master grows, a letter that was master-irrelevant is queued again — **must not** apply to (1)/(2) frozen letters. |

**Classification vs processing today**

- **Unanalyzed (user-facing):** not specified in code as one label; internally `discovered` / `queued` / `analyzing` (and rows with no finished scan).
- **After successful `finish_analysis`:** always `analyzed`. Relevant/Not Relevant is **derived** from `codes` ∩ `programs` and presence of `fields`, not stored.
- **After `fail_analysis` without prior extraction:** `failed` + `last_error` — not treated as Not Relevant in UI (`failed` filter, not `irrelevant`).
- **Master-only irrelevant:** `analyzed`, `fields=null`, `complete=false` — shows as analyzed but not “complete”; **not** Not Relevant in the §2 sense (no complete classification).

## 3. Functional requirements

### FR-WA-1 — Three-path relevance predicate

**Rule:** Introduce a single domain function (e.g. on `Extraction` or a small `bot/domain/relevance.py` module) used by extractor, UoW, and tests:

`is_relevant(extraction, programs) -> bool` is true iff **any**:

1. **Exact-string bypass (spec §2.1):** either exact substring is present in the letter document text used for extraction:
   - `כספים קואליציוניים: כן`
   - `יישום הסכמים פוליטיים בעלי משמעות תקציבית`  
   Match is **literal** on the text the loader exposes for search (same surface as deterministic field parsing — typically `letter.doc.text` and/or `markdown`; pick one and document in code). **No** OCR fuzzy/near-miss (locked).

2. **LLM bypass:** path (1) strings are **absent**, and persisted `fields.coalition_funds == "כן"` (after the existing `LlmAnalyzer` call).

3. **Master-code match:** normalized 6-digit code from the budget table (`Extraction.codes()`) is in `programs`.

**Acceptance:** Unit tests cover each path alone, combined paths, and “none → false”. `relevant_to(programs)` becomes an alias or thin wrapper around `is_relevant` so call sites migrate without drift.

---

### FR-WA-2 — Extractor pipeline order and “complete scan”

**Rule:** Change `Extractor.extract()` so classification matches §2:

1. Load letter; build table (as today).
2. Evaluate path (1) on document text **before** skipping the LLM.
3. Evaluate path (3) via `codes()` ∩ `master` (as today).
4. **Run the LLM** whenever a complete scan is required to decide (2) or to populate fields for a letter that may be Relevant via (1), (2), or (3). Concretely: run LLM if path (1) **or** path (3) **or** path (2) must be evaluated — i.e. always run LLM except where the implementation can prove (2) unnecessary **only** when (1) already made the letter Relevant **and** (3) is false? Spec: “if those strings are absent, the existing `coalition_funds` LLM call **still runs**.” So:
   - If (1) true → Relevant; still run LLM for coalition + program uses (and other fields).
   - If (1) false and (3) true → run LLM (today’s path).
   - If (1) false and (3) false → **still run LLM** for (2); then Relevant iff `coalition_funds == "כן"`, else **Not Relevant after complete scan**.

5. **Not Relevant (complete):** persist full `fields` (and letterhead/history as today), `analysis_status='analyzed'` via `finish_analysis` — **not** `fields=null`.

6. Keep arithmetic / heading / required-field failures as **`ExtractionError`** → `fail_analysis` (Error), not Not Relevant.

**Acceptance:** A letter with no master overlap and `coalition_funds="לא"` ends `analyzed`, `complete=true`, `is_relevant=false`. A former early-return irrelevant letter behaves per above (behavior change from current PRD FR-5). Golden/extraction tests updated accordingly.

---

### FR-WA-3 — Provenance payload for paths (1) and (2)

**Rule:** When Relevant via (1) or (2), attach an **immutable** provenance record on the versioned extraction JSON (bump `SCHEMA_VERSION` in `bot/domain/versions.py`). Use the spec’s grounding text verbatim:

- (1): `Relevant due to explicit presence of Coalition Funds / Political Agreements clauses, independent of master program matching.`
- (2): `Relevant due to coalition_funds = כן, independent of master program matching.`

Do **not** add a new Postgres column name in this workstream (locked: do not invent provenance column names). Provenance lives in `extraction` JSON only.

**Acceptance:** Round-trip `to_json` / `from_json` preserves provenance. Relevant via (3) has **no** provenance record. Re-analyze does not clear provenance if the letter still qualifies via (1) or (2) (recompute on each successful analysis).

---

### FR-WA-4 — Freeze against master resync (paths (1) and (2))

**Rule:** `is_relevant(extraction, programs)` returns **true** if provenance is set for (1) or (2), **even when** `codes ∩ programs` is empty after a master upload removes all overlapping codes.

Path (3) remains **recomputed** from current `programs` only (no freeze).

**Acceptance:** `test_newly_relevant_letter_needs_llm` unchanged for master-only letters. New test: letter Relevant only via (2), programs table cleared/replaced → still `is_relevant`, `request_analysis` returns `done`, not `queued`. Same for (1) with exact string fixture.

---

### FR-WA-5 — SQL and repository alignment

**Rule:** Replace master-only `RELEVANT` / `auto_eligible` predicates with the same semantics as `is_relevant`:

- `web/views/letters.py`: `RELEVANT` expression must be true for frozen provenance in JSON **or** `coalition_funds = 'כן'` in `extraction->'fields'` **or** `codes && programs`. (Exact JSON paths follow the implementer’s provenance key; keep one key documented in `extraction.py`.)
- `bot/adapters/postgres/letters.py` `auto_eligible`: same predicate + `complete` (fields object) + existing send guards.

**Acceptance:** `tests/test_postgres_repositories.py::test_auto_eligible_*` extended: bypass-relevant letter with no code overlap is eligible; master-only irrelevant with complete fields is not.

---

### FR-WA-6 — Post-scan state mapping (Unanalyzed / Error / Relevant / Not Relevant)

**Rule:** After one drain cycle:

| Condition | `analysis_status` | User-facing classification (§3.2 — implemented in other workstreams for labels) |
|---|---|---|
| Never finished scan; internal queue | `discovered` / `queued` / `analyzing` | **Unanalyzed** |
| `fail_analysis`, no saved extraction | `failed` | **Error** (not Not Relevant) |
| `finish_analysis`, `is_relevant` true | `analyzed` | **Relevant** |
| `finish_analysis`, complete, `is_relevant` false | `analyzed` | **Not Relevant** |
| `fail_analysis` but prior extraction exists | `analyzed` | Keep prior relevance from saved JSON |

**Acceptance:** `irrelevant` API filter matches `extraction IS NOT NULL AND NOT <RELEVANT>` and **excludes** `failed`. `needs_analysis` remains `RELEVANT AND NOT COMPLETE` (Relevant but missing fields — should be rare once FR-WA-2 ships).

---

### FR-WA-7 — Downstream send and render gates

**Rule:** `send_letter`, `auto_eligible`, and `attachments`/`render` paths use `is_relevant`, not raw `codes && programs`. Summary PDF is produced only when relevant (existing product rule); `named_matches(programs)` may be empty for (1)/(2)-only letters — renderer/report must tolerate empty master map (no crash).

**Acceptance:** `tests/test_send_letter.py` and send-job tests pass with a coalition-only relevant fixture.

---

### FR-WA-8 — Update extraction PRD alignment note

**Rule:** Add a short section to `docs/PRD-extraction-and-relevance.md` (or a linked addendum paragraph): **FR-5 relevance gate** is superseded for product behavior by agent spec §2; master match is path (3) only; coalition and exact strings are paths (2) and (1). Do not rewrite extraction field tools.

**Acceptance:** Doc diff is ≤1 screen; points to spec §2.

## 4. Files to change (repo-relative paths)

- `bot/domain/extraction.py` — predicate, extractor flow, JSON provenance, `relevant_to` → `is_relevant`
- `bot/domain/versions.py` — `SCHEMA_VERSION` bump if JSON shape changes
- `bot/service_layer/analysis.py` — `request_analysis` “done” / requeue logic
- `bot/adapters/postgres/letters.py` — `auto_eligible` WHERE clause
- `web/views/letters.py` — `RELEVANT` SQL expression
- `bot/service_layer/sending.py` — send gate
- `bot/service_layer/services.py` — any inline relevance checks in local extract helpers
- `bot/tests/fixtures/extractions.py` — fixtures for bypass / complete-not-relevant
- `bot/tests/test_extraction_t6.py`, `bot/tests/test_extraction_json.py`, `tests/test_analysis_queue.py`, `tests/test_postgres_repositories.py`, `tests/test_letters_api.py` (if filters break)
- `docs/PRD-extraction-and-relevance.md` — FR-5 supersession note (FR-WA-8)

Optional thin module `bot/domain/relevance.py` only if it avoids circular imports; prefer colocation in `extraction.py` unless messy.

## 5. Tests to add/update

1. **Exact string (1):** fixture text containing `כספים קואליציוניים: כן` without master codes → relevant, provenance (1), LLM invoked (mock).
2. **Coalition (2):** no exact strings, no master overlap, mock LLM `כן` → relevant, provenance (2).
3. **Master (3):** existing golden / `complete_extraction` behavior preserved.
4. **Not Relevant complete:** no paths → `fields` populated, `is_relevant` false.
5. **Freeze:** (2)-relevant letter, delete overlapping program row → still relevant; master-only letter still re-queues when program added (`test_newly_relevant_letter_needs_llm`).
6. **SQL:** list filter / `auto_eligible` for bypass letter without `codes && programs`.
7. **Error:** `fail_analysis` without extraction → `failed`, not counted in `irrelevant` filter.

Do **not** add tests for: retry policy, LLM-down behavior, OCR near-miss on exact strings (explicitly out of spec).

## 6. Out of scope for this workstream

- Table filters / Hebrew labels (`לא נותחו`, `תקלה`, `דורש עיון`, dropping Sent / Old Version filters) — UI workstream
- `passed` boolean / `עברה` / `לא עברה`
- Excel export, mailing list, notifications
- Changing `coalition_funds` LLM prompts beyond what’s required to read `כן` for path (2)
- Error retry, LLM-unavailable handling
- Provenance **column** names or admin UI for provenance

## 7. Resume

If this job stopped mid-implementation, read **spec §2–§2.1** (`Berl Katznelson Monitor - Agent System Specification.md` at repo root) and **`bot/domain/extraction.py`** (current early-return before LLM is the main gap). **`web/views/letters.py`** `RELEVANT` and **`letters.auto_eligible`** must use the same predicate as **`is_relevant`** including JSON provenance and `coalition_funds`. **`bot/service_layer/analysis.py`** `request_analysis` must treat frozen bypass letters as `done`. Do not redo PRD text; implement FR-WA-1–7 in order (predicate → extractor → JSON schema → SQL → send gates → tests). Do not implement table-filter UX or Passed flag.

---

## Agent notes (verification)

- Read spec §2–§2.1 from `/Users/dafna/Documents/berl-moni/Berl Katznelson Monitor - Agent System Specification.md` (file absent from worktree; content matches task locked decisions).
- Opened `bot/domain/extraction.py`, `bot/adapters/postgres/letters.py`, `bot/service_layer/analysis.py`, `web/views/letters.py`, `docs/PRD-extraction-and-relevance.md`, and grep-traced `relevant_to` / `RELEVANT` call sites.
- Cross-checked: current behavior is master-only early LLM skip; contradicts §2 paths (1)(2) and “complete scan → Not Relevant.”

### OPEN ITEMS

- Spec file not present in the delegated worktree path; implementers should copy or symlink from main repo if hooks expect it in `pwd`.
- Exact JSON key for provenance left to implementation (per “do not invent provenance column names”); FR-WA-3 requires one documented key in code only.
