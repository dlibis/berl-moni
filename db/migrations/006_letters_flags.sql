-- Workstream B: manual review and pass/fail decision flags on letters.
ALTER TABLE letters
  ADD COLUMN IF NOT EXISTS requires_review boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS passed boolean NOT NULL DEFAULT false;
