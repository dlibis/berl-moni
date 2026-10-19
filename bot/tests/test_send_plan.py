
from bot.domain import send_plan

MB = 1024 * 1024
# 15 MB raw encodes to exactly 20 MB, so two of them cannot share a 24 MB batch
RAW_20MB_ENCODED = 15 * MB
ONE = ["a@example.com"]


def test_two_batches_for_40mb_encoded():
    # Raw 40 MB would need three batches (it encodes to 53 MB), so "40MB" here is encoded
    letters = [("l0", RAW_20MB_ENCODED), ("l1", RAW_20MB_ENCODED)]
    out, oversized = send_plan.batches(letters)
    assert [[u for u, _ in b] for b in out] == [["l0"], ["l1"]]
    assert oversized == []


def test_pdf_over_cap_is_oversized_and_not_batched():
    letters = [("big", 40 * MB), ("small", 1000)]
    out, oversized = send_plan.batches(letters)
    assert oversized == [("big", 40 * MB)]
    assert out == [[("small", 1000)]]


def test_batch_order_preserved():
    letters = [(f"l{i}", int(7.5 * MB)) for i in range(5)]  # 10 MB encoded: two per batch
    out, _ = send_plan.batches(letters)
    assert [[u for u, _ in b] for b in out] == [["l0", "l1"], ["l2", "l3"], ["l4"]]


def test_chunks_of_49():
    recipients = [f"r{i}" for i in range(100)]
    parts = send_plan.chunks(recipients)
    assert [len(c) for c in parts] == [49, 49, 2]
    assert [r for c in parts for r in c] == recipients


def test_emails_needed_math():
    assert send_plan.emails_needed(2, send_plan.chunks([f"r{i}" for i in range(100)])) == 206
    assert send_plan.emails_needed(1, [["a", "b", "c"]]) == 4


def test_over_budget_drops_newest_batch():
    batches = [["b0"], ["b1"], ["b2"]]
    # one recipient -> 2 emails per batch; daily cap 5 fits two batches (4), not three (6)
    assert send_plan.fit_budget(batches, [ONE], 0, 0, 5, 0, 1000) == [["b0"], ["b1"]]


def test_monthly_limit_also_applies():
    batches = [["b0"], ["b1"], ["b2"]]
    assert send_plan.fit_budget(batches, [ONE], 0, 0, 100, 0, 3) == [["b0"]]


def test_nothing_fits_returns_empty():
    batches = [["b0"]]
    assert send_plan.fit_budget(batches, [ONE], 0, 0, 10, 10, 1000) == []


def test_idempotency_key_format():
    assert send_plan.idempotency_key(7, 2, 1) == "run7-b2-c1"


def test_chunk_size_matches_the_web_screens():
    from common.limits import CHUNK
    assert send_plan.CHUNK_SIZE == CHUNK
