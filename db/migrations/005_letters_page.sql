ALTER TABLE letters
    ADD COLUMN IF NOT EXISTS analysis_status text NOT NULL DEFAULT 'discovered'
        CHECK (analysis_status IN ('discovered', 'queued', 'analyzing', 'analyzed', 'failed')),
    ADD COLUMN IF NOT EXISTS letter_date date,
    ADD COLUMN IF NOT EXISTS ministry text,
    ADD COLUMN IF NOT EXISTS request_numbers text[],
    ADD COLUMN IF NOT EXISTS feed_rows jsonb,
    ADD COLUMN IF NOT EXISTS first_seen_at timestamptz NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS last_seen_in_feed_at timestamptz,
    ADD COLUMN IF NOT EXISTS extraction jsonb,
    ADD COLUMN IF NOT EXISTS codes text[],
    ADD COLUMN IF NOT EXISTS extraction_version text,
    ADD COLUMN IF NOT EXISTS analyzed_at timestamptz,
    ADD COLUMN IF NOT EXISTS source_sha256 text,
    ADD COLUMN IF NOT EXISTS source_size int,
    ADD COLUMN IF NOT EXISTS last_error text,
    ADD COLUMN IF NOT EXISTS last_error_at timestamptz,
    ADD COLUMN IF NOT EXISTS lease_id uuid,
    ADD COLUMN IF NOT EXISTS lease_expires_at timestamptz,
    ADD COLUMN IF NOT EXISTS attempts int NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS analysis_requested_by text,
    ADD COLUMN IF NOT EXISTS last_sent_at timestamptz,
    ADD COLUMN IF NOT EXISTS send_count int NOT NULL DEFAULT 0;

ALTER TABLE letters ALTER COLUMN status DROP NOT NULL;

CREATE INDEX IF NOT EXISTS letters_table_order
    ON letters (letter_date DESC NULLS LAST, letter_url);
CREATE INDEX IF NOT EXISTS letters_queue
    ON letters (analysis_status) WHERE analysis_status IN ('queued', 'analyzing');

ALTER TABLE send_runs
    ADD COLUMN IF NOT EXISTS kind text NOT NULL DEFAULT 'auto'
        CHECK (kind IN ('auto', 'manual')),
    ADD COLUMN IF NOT EXISTS requested_by text;

DROP INDEX IF EXISTS send_runs_one_per_day;
CREATE UNIQUE INDEX IF NOT EXISTS send_runs_one_auto_per_day ON send_runs (day)
    WHERE kind = 'auto' AND status IN ('sending', 'sent', 'abandoned');

ALTER TABLE email_log
    ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'sent'
        CHECK (status IN ('sending', 'sent', 'unknown')),
    ADD COLUMN IF NOT EXISTS started_at timestamptz,
    ADD COLUMN IF NOT EXISTS resend_email_id text;

UPDATE letters
SET analysis_status = 'analyzed', first_seen_at = scanned_at
WHERE analysis_status = 'discovered' AND extraction IS NULL AND status = 'pending';

UPDATE letters
SET first_seen_at = scanned_at
WHERE analysis_status = 'discovered' AND extraction IS NULL AND status = 'irrelevant'
  AND first_seen_at IS DISTINCT FROM scanned_at;

UPDATE letters
SET analysis_status = 'failed', last_error = reason, first_seen_at = scanned_at
WHERE analysis_status = 'discovered' AND extraction IS NULL AND status = 'failed';

UPDATE letters
SET last_sent_at = sent_at, send_count = 1, first_seen_at = scanned_at
WHERE analysis_status = 'discovered' AND extraction IS NULL AND status = 'sent'
  AND send_run_id IS NOT NULL AND send_count = 0;

UPDATE letters
SET first_seen_at = scanned_at
WHERE analysis_status = 'discovered' AND extraction IS NULL AND status = 'sent'
  AND send_run_id IS NULL AND send_count = 0
  AND first_seen_at IS DISTINCT FROM scanned_at;
