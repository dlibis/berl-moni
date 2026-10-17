"""Send plan for the send job: attachment batches, recipient chunks, and the email budget.

Pure functions. No database, no network.
"""
import math

# Resend rejects an email over 40 MB including its attachments after Base64 encoding; 35 MB of
# encoded PDFs leaves room for the body and the MIME headers.
MAX_BATCH_BYTES = 35 * 1024 * 1024
# Resend takes at most 50 addresses per message: the reply-to inbox in `to`, so 49 in `bcc`.
# Must equal common.limits.CHUNK, which the web screens use for the same arithmetic.
CHUNK_SIZE = 49


def encoded_size(pdf_bytes):
    # Base64: every 3 bytes become 4 characters
    return math.ceil(pdf_bytes / 3) * 4


def batches(letters):
    """letters: ordered (letter_url, pdf_bytes_len) pairs, oldest first.

    Returns (batches, oversized). Each batch is an ordered list of the same pairs.
    A PDF whose encoded size alone exceeds the cap goes to oversized, never into a batch.
    """
    out, oversized, current, size = [], [], [], 0
    for letter in letters:
        n = encoded_size(letter[1])
        if n > MAX_BATCH_BYTES:
            oversized.append(letter)
            continue
        if current and size + n > MAX_BATCH_BYTES:
            out.append(current)
            current, size = [], 0
        current.append(letter)
        size += n
    if current:
        out.append(current)
    return out, oversized


def chunks(recipients, size=CHUNK_SIZE):
    return [recipients[i:i + size] for i in range(0, len(recipients), size)]


def emails_needed(n_batches, chunks):
    return n_batches * sum(len(c) + 1 for c in chunks)


def within_budget(needed, sent_today, sent_month, daily_limit, reserve, monthly_limit):
    """True if `needed` more emails fit today's usable budget and this month's."""
    return needed + sent_today <= daily_limit - reserve and needed + sent_month <= monthly_limit


def fit_budget(batches, chunks, sent_today, sent_month, daily_limit, reserve, monthly_limit):
    """Keep the oldest batches that fit both budgets. Returns [] when none fits."""
    for kept in range(len(batches), -1, -1):
        if within_budget(emails_needed(kept, chunks), sent_today, sent_month, daily_limit, reserve, monthly_limit):
            return batches[:kept]
    return []


def idempotency_key(run_id, batch, chunk):
    return f"run{run_id}-b{batch}-c{chunk}"
