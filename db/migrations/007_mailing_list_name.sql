-- Subscriber display name (§4). Existing email-only rows backfill to empty string;
-- API rejects new POSTs without a non-empty trimmed name.
ALTER TABLE mailing_list ADD COLUMN IF NOT EXISTS name text NOT NULL DEFAULT '';

UPDATE mailing_list SET name = '' WHERE name IS NULL;
ALTER TABLE mailing_list ALTER COLUMN name SET DEFAULT '';
ALTER TABLE mailing_list ALTER COLUMN name SET NOT NULL;

INSERT INTO settings (key, value) VALUES ('always_send', 'false'::jsonb)
ON CONFLICT (key) DO NOTHING;
