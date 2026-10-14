CREATE TABLE programs (
    code text PRIMARY KEY CHECK (code ~ '^[0-9]{6}$'),
    name text NOT NULL
);

CREATE TABLE mailing_list (
    email text PRIMARY KEY CHECK (email = lower(btrim(email)) AND email <> '')
);

CREATE TABLE settings (
    key text PRIMARY KEY,
    value jsonb NOT NULL
);

CREATE TABLE send_runs (
    id bigserial PRIMARY KEY,
    day date NOT NULL,
    status text NOT NULL CHECK (status IN ('sending', 'sent', 'failed', 'abandoned')),
    started_at timestamptz NOT NULL DEFAULT now(),
    failed_at timestamptz,
    finished_at timestamptz,
    resume_requested_at timestamptz,
    error text,
    from_address text NOT NULL,
    reply_to_address text NOT NULL,
    recipients jsonb,
    batches jsonb NOT NULL
);

CREATE UNIQUE INDEX send_runs_one_per_day ON send_runs (day)
    WHERE status IN ('sending', 'sent', 'abandoned');

CREATE TABLE letters (
    letter_url text PRIMARY KEY,
    slug text NOT NULL UNIQUE,
    status text NOT NULL CHECK (status IN ('irrelevant', 'failed', 'pending', 'sent')),
    reason text CHECK (reason IN ('quota', 'network', 'provider_5xx', 'extract_error', 'render_error')),
    summary_pdf bytea,
    pdf_bytes int,
    scanned_at timestamptz NOT NULL DEFAULT now(),
    sent_at timestamptz,
    send_run_id bigint REFERENCES send_runs (id),
    CHECK (reason IS NULL OR status = 'failed')
);

CREATE TABLE scans (
    id bigserial PRIMARY KEY,
    ran_at timestamptz NOT NULL DEFAULT now(),
    day date NOT NULL,
    status text NOT NULL CHECK (status IN ('sent', 'nothing_new', 'failed')),
    reason text CHECK (reason IN ('missing_settings', 'list_over_cap', 'feed_unreachable', 'quota',
                                  'over_budget', 'resend_error', 'send_run_stuck')),
    letters_in_feed int,
    new_letters int NOT NULL DEFAULT 0,
    relevant int NOT NULL DEFAULT 0,
    failed int NOT NULL DEFAULT 0,
    emails_sent int NOT NULL DEFAULT 0
);

CREATE INDEX scans_day ON scans (day);

CREATE TABLE email_log (
    idempotency_key text PRIMARY KEY,
    sent_at timestamptz NOT NULL DEFAULT now(),
    emails int NOT NULL,
    kind text NOT NULL CHECK (kind IN ('letter', 'test'))
);
