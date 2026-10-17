-- T6: a summary PDF too big to attach to any email is failed / pdf_too_large (it was render_error).
ALTER TABLE letters DROP CONSTRAINT letters_reason_check;
ALTER TABLE letters ADD CONSTRAINT letters_reason_check
    CHECK (reason IN ('quota', 'network', 'provider_5xx', 'extract_error', 'render_error', 'no_text', 'pdf_too_large'));
