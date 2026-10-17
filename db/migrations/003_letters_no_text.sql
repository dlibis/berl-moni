-- T6: a scanned letter that OCR can't read is recorded as failed / no_text.
ALTER TABLE letters DROP CONSTRAINT letters_reason_check;
ALTER TABLE letters ADD CONSTRAINT letters_reason_check
    CHECK (reason IN ('quota', 'network', 'provider_5xx', 'extract_error', 'render_error', 'no_text'));
