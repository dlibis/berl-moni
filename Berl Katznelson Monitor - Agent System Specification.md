# Israeli Finance Committee Monitor Agent (Berl Katznelson)

Technical and agent specification. This file is the whole spec (no §4.2).

## 1. System Overview

The agent monitors government financial proposals (*Pniyot* / פניות) on the Knesset Finance Committee portal: fetch publications, OCR and parse PDFs, classify relevance against master program codes plus the bypass rules in §2, and serve structured payloads for audit and export.

## 2. Relevance

A request is **Relevant** if **any** of these is true. Otherwise, after a **complete** scan, it is **Not Relevant**. An **Error** is not Not Relevant.

1. **Exact-string bypass** — any of these strings is present in the document text (no master-code check):
   - `כספים קואליציוניים: כן` (Coalition Funds: Yes)
   - `יישום הסכמים פוליטיים בעלי משמעות תקציבית` (Implementation of political agreements with budgetary significance)
2. **LLM bypass** — if those strings are absent, the existing `coalition_funds` LLM call still runs. An answer of `כן` also marks Relevant and also skips the master-code check.
3. **Master-code match** — a 6-digit program code in the document is in the active Master Program Code list.

### 2.1 Provenance

When Relevant via (1) or (2), attach an immutable provenance record on the payload so a later master-list resync cannot override that Relevant. Grounding:

- (1): `Relevant due to explicit presence of Coalition Funds / Political Agreements clauses, independent of master program matching.`
- (2): `Relevant due to coalition_funds = כן, independent of master program matching.`

Path (3) is not frozen against master resync.

## 3. Names and table

### 3.1 Terminology

All user-facing, system-level, and API references use **Pniyot** (Requests / פניות), not **Machtavim** (Letters / מכתבים).

### 3.2 What the table shows

These are **table filters / row labels**, not one stored enum.

| Key | Hebrew | Kind | Rule |
|---|---|---|---|
| All Requests | כל הפניות | View | Every ingested row. |
| Unanalyzed | לא נותחו | Processing (user-facing) | Ingested, not yet classified. Covers internal `discovered` / `queued` / `analyzing`. |
| Error | תקלה | Exception | Network timeout, OCR failure, or bad PDF. Replaces *Failed* (`נכשלו`). |
| Requires Review | דורש עיון | Manual flag | Person pins a row. **Never** set by the pipeline. Independent of classification and of Requires Analysis. |
| Requires Analysis | דורשים ניתוח | Auto flag | Relevant, but extraction is incomplete. Pipeline-assigned. Keep; do not replace with Requires Review. |
| Relevant | רלוונטי | Output | §2 path (1), (2), or (3). |
| Not Relevant | לא רלוונטי | Output | Complete scan; none of the §2 paths. |

**Not in the table**

- **Pending / In Queue (`בתור`)** — internal worker state only (scrape already produced a row; OCR / parse / LLM). No filter, no badge.
- **Sent (`נשלחו`)** — drop as a table filter. Sending mail still exists.
- **Old Version (`גרסה ישנה`)** — drop as a table filter.

### 3.3 Decision status

Independent of processing and of Relevant / Not Relevant.

- **Passed / Not Passed** (`עברה` / `לא עברה`)
- Boolean: `true` = Passed, `false` = Not Passed
- New rows are **Not Passed** until flipped to Passed
- Meaning: whether the committee has formally approved the request

## 4. Export, master list, notifications

**Dashboard and reporting**

- One-click Excel export of the primary requests table.
- The spreadsheet includes a hyperlink to the original Knesset PDF.

**Program master**

Excel (`.xlsx`) upload and download of the active 6-digit Master Program Code list.

**Notifications**

Subscriber fields (both required): `Email` (string), `Name` (string).

Dispatch: `Always Send` (`שלח תמיד`) — weekly cron, in parallel with custom date-range schedules.

## Not specified here

Do not invent: provenance column names, Error retry, LLM-unavailable behavior, Always Send overlapping a custom range, OCR near-miss on the §2 exact strings.
