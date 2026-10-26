# PRD — Agent spec, split for parallel subagents

Source of truth: `Berl Katznelson Monitor - Agent System Specification.md`  
Slices: `docs/prd/A-relevance.md` · `docs/prd/B-table.md` · `docs/prd/C-export.md`

Three independent workstreams. Fan them out. If a lane dies on a rate limit, **continue that slice only** — do not restart the others.

## Shared (every agent reads this)

- Spec file is currently **untracked**. Copy it into the worktree (`cp` from the main checkout) or commit it before `--worktree` fanout, or agents will miss it.
- Cloud lanes refuse a checkout that contains `.env`. Use `--worktree` (gitignored `.env` stays out).
- Never reopen locked spec decisions. Do not invent: provenance column names, Error retry, LLM-unavailable, Always Send overlapping a custom range, OCR near-miss.
- **Migration numbers (do not collide):** A writes no migration. B = `db/migrations/006_letters_flags.sql` (`requires_review`, `passed`). C = `db/migrations/007_mailing_list_name.sql` plus Always Send settings. If C also needs a programs/xlsx change, `008_…`.
- Do not rename the `letters` table or `/api/v1/letters` in this PRD.

## Workstreams

| ID | File | Owns | Does not touch |
|---|---|---|---|
| A | `docs/prd/A-relevance.md` | Relevance predicate, provenance JSON, extractor early-return, SQL `RELEVANT` / `auto_eligible`, send gate | Table filters, Hebrew labels, Excel, mailing list, `passed` |
| B | `docs/prd/B-table.md` | Pniyot copy, filters/badges, hide `בתור`, Unanalyzed includes queue, drop Sent/Old Version filters, `דורש עיון`, `passed` | How relevance is computed, export, notify |
| C | `docs/prd/C-export.md` | Excel export + PDF hyperlink, master xlsx up/down, subscriber `Name`, Always Send weekly | Relevance, status taxonomy |

Each slice has **§7 Resume**: files to re-read and what not to redo.

## Rate-limit pickup

1. Classify the dead job. If it printed `OSRC::DONE` and the slice file is on disk, **REUSE-OUTPUT** — stitch, do not rerun.
2. If it died mid-write: relaunch **that one agent** with `--worktree`, same slice file as input: “read `docs/prd/<slice>.md` and continue from §7 Resume; do not restart finished FRs.”
3. Swap lane if the previous one is limited (Cursor Composer → Grok on Cursor → Gemini Flash). Never Devin, never Fable.
4. Commit per workstream when its tests pass so the next agent can `git pull` a stable base.

## Fanout (implementation)

One job per slice, `--worktree`, unique branch. Merge A/B/C after each is green. B and C both touch `web/views/letters.py` — merge A first (predicate), then B (filters), then C (export) **or** have C only add an export route and not rewrite `FILTERS`.
