from datetime import date

import psycopg
from psycopg.rows import dict_row

from bot.adapters.postgres.letters import LettersRepository
from bot.domain.feed import Approval, FeedLetter


def test_refresh_preserves_reports_manual_pass_and_first_detection(test_db_url):
    with psycopg.connect(test_db_url, row_factory=dict_row) as conn:
        repo = LettersRepository(conn)
        repo.upsert_feed([FeedLetter('passage-test-url', None, '', ('43-206,17-211',), ())], False)
        conn.execute("UPDATE letters SET passed = true, extraction = '{\"saved\":true}'::jsonb "
                     "WHERE letter_url = 'passage-test-url'")
        approval = Approval(('17-211,43-206',), date(2026, 10, 21))
        repo.record_approvals([approval])
        first = conn.execute("SELECT * FROM letters WHERE letter_url = 'passage-test-url'").fetchone()
        repo.record_approvals([approval])
        repo.upsert_feed([FeedLetter('passage-test-url', None, '', ('43-206,17-211',), ())], True)
        last = conn.execute("SELECT * FROM letters WHERE letter_url = 'passage-test-url'").fetchone()
        assert last['passed'] and last['passed_date'] == date(2026, 10, 21)
        assert last['passage_detected_at'] == first['passage_detected_at']
        assert last['extraction'] == {'saved': True}
        assert last['analysis_status'] == 'discovered'
        conn.rollback()
