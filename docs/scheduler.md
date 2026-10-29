# Worker scheduling

The hourly Neon Function Trigger calls `GET /api/internal/scheduler/tick` on the
existing Flask API. That endpoint checks the database and dispatches `letters.yml`
only when work is eligible. The GitHub job rechecks eligibility before starting
the worker. No OCR, feed fetch, analysis, or email runs in the scheduler.

Eligibility includes custom sends, Sunday 09:00 Asia/Jerusalem Always Send,
configured feed cadence, requested resumes, queued analysis, and expired leases.
The app's schedule remains the source of truth; editing it needs no redeploy.
After a `nothing_new` scan, the existing due rules permit another attempt that
day. Manual analysis and Resume dispatch immediately; failures wait for the next
hourly tick. Manual feed refresh queues automatic analysis for that tick.

## Configuration

- Vercel production: `SCHEDULER_SECRET` and the existing `GITHUB_DISPATCH_TOKEN`.
- Neon function `scheduler`: the same `SCHEDULER_SECRET` and
  `SCHEDULER_TICK_URL=https://<production-origin>/api/internal/scheduler/tick`.
- Neon trigger `letters-hourly`: `0 * * * *` UTC, path `/`, production branch only.
- No Vercel Cron, `pg_cron`, database migration, or billing upgrade is needed.

Generate a random secret with at least 32 bytes of entropy. Store it in the
providers' environment settings, never in the repository or command history.
The function accepts only Neon-authenticated trigger calls, uses a 20-second
timeout, refuses redirects, and requires a recognized JSON response from Flask.
The Flask endpoint requires the shared bearer secret and always disables caching.

The endpoint takes a transaction-level advisory lock, bounded by a 5-second lock
timeout. Successful scheduled dispatches save their UTC hour in the existing
`settings.scheduler_last_dispatched_hour` value (the settings key, not a column).
Duplicate ticks in that hour do not dispatch again. Failed dispatches do not save
the hour. GitHub dispatch and the DB commit are not atomic: a timeout or failed
commit after GitHub accepts can cause a redundant workflow. Existing workflow
concurrency, eligibility checks, analysis leases, and send protections still apply.

## Validation and cutover

1. Run the focused Python suites and `node --test functions/scheduler/index.test.mjs`.
2. Configure the secret in Vercel and deploy the app, keeping GitHub schedules active.
3. Confirm missing/wrong credentials return 401 and an authenticated idle tick
   returns `{"status":"idle"}` without creating a GitHub run. A due tick starts
   real work, so do not use a production tick as a harmless health check.
4. Deploy `functions/scheduler/index.ts` with slug `scheduler` to the existing
   production branch; use the Console environment editor for secrets. The CLI
   supports `neon functions deploy scheduler --src functions/scheduler/index.ts`.
5. Create a disabled `letters-hourly` schedule trigger. Enable it after reviewing
   its branch, function URL, app URL, and environment. Validate a real trigger
   invocation; ordinary requests cannot spoof Neon's trusted header.
6. Once a trigger invocation succeeds, remove `on.schedule` from `letters.yml`
   and retire `always_send.yml`. Preserve `workflow_dispatch`, the check job,
   worker secrets, and the `letters` concurrency group. Publish those workflow
   changes only after the Neon replacement is confirmed.
7. Confirm the trigger's hourly cadence, inspect the next due worker run, and
   watch for failed ticks. Neon Function logs show HTTP status; Flask logs show
   tick hour and outcome. Neither logs secrets or source documents.

An idle tick must create no Actions run. A due tick dispatches once per UTC hour;
repeated/concurrent ticks do not dispatch again. Database or GitHub errors return
503 and remain eligible for the next tick. Scheduler downtime delays sends and
recovery; inspect failed invocations rather than relying on immediate retries.

## Rollback

Disable `letters-hourly` in Neon, restore the previous hourly and weekly GitHub
schedules, and publish the workflow restoration. Keep `letters.yml` enabled:
disabling it also blocks manual analysis and recovery dispatches. If reverting
the Vercel app, restore the GitHub fallback first. Do not change schedule data,
delete queued work, or disable database scale to zero.

Neon availability and limits: [Function Triggers](https://neon.com/docs/compute/functions/triggers/schedule),
[environment variables](https://neon.com/docs/compute/functions/environment-variables),
[pricing](https://neon.com/pricing). Hourly means roughly 720–744 calls per month;
the project's other function and database usage still counts toward its allowances.

## Initial cutover evidence (2026-10-29)

- Existing project `solitary-rice-27550522`, branch `production`, Free plan;
  no billing or database compute settings changed.
- Function slug `scheduler`; trigger `letters-hourly`, ID
  `trigger-77e9454c-3fd1-48ca-9433-fbb4e5804494`.
- Live endpoint on `https://berl.site`: missing/wrong secret returned 401;
  authenticated idle tick returned 200 with `Cache-Control: no-store`.
- A forged Neon trigger header was stripped and the function returned 403.
- Real scheduled invocation at `2026-10-29T10:51:02Z` logged HTTP 200;
  cadence then restored from temporary minutely verification to hourly.
- Vercel rollback target before this release:
  `https://berl-moni-r2micn1t0-dlibis-projects.vercel.app`.
- Local validation: 105 Python tests against test Postgres and the Node HTTP
  self-check passed. No real email or model call was used for testing.
- The next genuinely due worker run remains an operational follow-up; idle
  verification does not prove delivery of scheduled email or model analysis.
