INSERT INTO settings (key, value) VALUES
    ('schedule', '[]'),
    ('from_address', '""'),
    ('reply_to_address', '""'),
    ('resend_daily_limit', '100'),
    ('resend_monthly_limit', '3000'),
    ('resend_reserve', '5')
ON CONFLICT (key) DO NOTHING;
