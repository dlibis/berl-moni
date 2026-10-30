ALTER TABLE letters
    ADD COLUMN IF NOT EXISTS passed_date date,
    ADD COLUMN IF NOT EXISTS passage_detected_at timestamptz;
