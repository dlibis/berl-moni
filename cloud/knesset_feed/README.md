# Israeli Knesset fetch service

This service runs only the public Knesset feed and source-PDF requests in Cloud Run
`me-west1` (Tel Aviv). It has no database, model, email, or GitHub credentials.
GitHub retains the schedules, analysis, and send jobs; Vercel retains the app.

`GET /feed` uses the existing feed adapter and returns serialized `FeedLetter`
objects. `GET /pdf?url=...` accepts only HTTPS files under
`fs.knesset.gov.il/globaldocs/FINANCE/`, follows no redirects, rejects non-PDF
responses, and limits each PDF to 64 MiB. Both endpoints require
`Authorization: Bearer <KNESSET_FETCH_TOKEN>` and return `Cache-Control: no-store`.

## Deployment

Project: `berl-moni-fetch-20261026`, owned by `phoenix409@gmail.com`.
Service and Artifact Registry repository: `knesset-feed`, region `me-west1`.
`.gcloudignore` restricts the upload to the service and its feed/domain modules;
no `.env`, database, email, model, or client files are uploaded.

Build from the repository root with:

```sh
gcloud builds submit --project=berl-moni-fetch-20261026 \
  --account=phoenix409@gmail.com --region=me-west1 \
  --config=cloud/knesset_feed/cloudbuild.yaml .
```

Deploy the resulting Artifact Registry image with request-based billing,
1 vCPU, 512 MiB memory, zero minimum instances, one maximum instance, four
concurrent requests per instance, and a 300-second timeout. The runtime service
account needs no project roles. The Cloud Run endpoint permits invocation and
the application enforces the bearer token. Keep the token in a mode-600
temporary environment file when deploying; never put it on the command line,
in this repository, or in logs.

No static IP, VPC connector, NAT gateway, or additional scheduler is needed.
The free allowances are shared by billing account and are not a spending cap;
internet transfer from Israel and retained container images may incur charges.

## Callers and rollback

Set the service base URL as the GitHub repository variable `KNESSET_FETCH_URL`
and the token as repository secret `KNESSET_FETCH_TOKEN`. Both `letters.yml`
and `always_send.yml` pass these to the worker. Configure the same two variables
in the production Vercel project to cover the manual refresh button.

Local callers keep the existing direct Knesset path when `KNESSET_FETCH_URL` is
unset. A configured remote service failure never silently falls back to the
blocked cloud path. Removing the URL and redeploying restores direct fetching.
The PDF cache, original source URL, validation, and retry behavior are retained.

Verify a full feed and a PDF from the deployed service before updating either
caller. Do not dispatch a send workflow just to test connectivity: it can send
real mail and incur model charges.
