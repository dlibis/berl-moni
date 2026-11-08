# Israeli Knesset fetch service

This service runs only the public Knesset feed and source-PDF requests in Cloud Run
`me-west1` (Tel Aviv). It has no database, model, email, or GitHub credentials.
Neon triggers the schedule checks; GitHub runs analysis and send jobs; Vercel hosts the app.

`GET /feed` uses the existing feed adapter and returns serialized `FeedLetter`
objects. `GET /approvals` returns all approved request-number sets with nullable
`approved_date` values, without fetching PDFs. It uses bounded parallel pagination
and fails if the page counts are inconsistent. `GET /pdf?url=...` accepts only HTTPS files under
`fs.knesset.gov.il/globaldocs/FINANCE/`, follows no redirects, rejects non-PDF
responses, and limits each PDF to 64 MiB. All three endpoints require
`Authorization: Bearer <KNESSET_FETCH_TOKEN>` and return `Cache-Control: no-store`.

## Deployment

For transferring management or recreating this service in another Google
account/project, see [the account migration runbook](../../docs/cloud-run-account-migration.md).

Project: `moni-510609` (project number `998754133296`).
Service and Artifact Registry repository: `knesset-feed`, region `me-west1`.
`.gcloudignore` restricts the upload to the service and its feed/domain modules;
no `.env`, database, email, model, or client files are uploaded.

Build from the repository root with:

```sh
gcloud builds submit --project=moni-510609 \
  --region=me-west1 \
  --service-account=projects/moni-510609/serviceAccounts/knesset-build@moni-510609.iam.gserviceaccount.com \
  --config=cloud/knesset_feed/cloudbuild.yaml .
```

The dedicated builder can read staged source, write images in this repository,
and write Cloud Logging build logs. These permissions are separate from the
runtime service account, which has no project roles.

Live service base URL: `https://knesset-feed-998754133296.me-west1.run.app`.

Deploy the resulting Artifact Registry image with request-based billing,
1 vCPU, 512 MiB memory, zero minimum instances, one maximum instance, four
concurrent requests per instance, and a 300-second timeout. The runtime service
account `knesset-runtime@moni-510609.iam.gserviceaccount.com` has no project roles.
Cloud Run permits invocation only by the configured GitHub and Vercel caller
identities; the application also enforces the bearer token. See the
[IAM authentication setup](../../docs/cloud-run-iam-auth.md). Keep the token in a mode-600
temporary environment file when deploying; never put it on the command line,
in this repository, or in logs.

No static IP, VPC connector, NAT gateway, or additional scheduler is needed.
The free allowances are shared by billing account and are not a spending cap;
internet transfer from Israel and retained container images may incur charges.

## Callers and rollback

Set the service base URL as the GitHub repository variable `KNESSET_FETCH_URL`
and the token as repository secret `KNESSET_FETCH_TOKEN`. `letters.yml`
passes these to the worker. Configure the same two variables
in the production Vercel project to cover the manual refresh button.

Local callers keep the existing direct Knesset path when `KNESSET_FETCH_URL` is
unset. A configured remote service failure never silently falls back to the
blocked cloud path. Removing the URL and redeploying restores direct fetching.
The PDF cache, original source URL, validation, and retry behavior are retained.

Verify a full feed and a PDF from the deployed service before updating either
caller. Do not dispatch a send workflow just to test connectivity: it can send
real mail and incur model charges.

## Passage tracking rollout

Apply migration `008_letter_passage.sql`, deploy this service with `/approvals`,
then deploy the web/worker callers. Until the endpoint is available, the new
callers deliberately fail the refresh instead of silently skipping passage checks.
The approvals client uses one 200-second read timeout without retries; keep the
service and web function limits at 300 seconds. Existing pending-feed counts and
analysis scheduling are unchanged. Approval matching uses the complete normalized
request-number set, never the PDF URL. Conflicting approval dates are logged and
skipped. A successful refresh may mark an existing tracked letter passed, but
never automatically clears that flag or reanalyzes its report.
