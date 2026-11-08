# Move the Knesset fetch proxy to a completely new Google account

This runbook recreates the Knesset fetch service from scratch under a brand-new
Google account. You do not need access to the old account to follow it, except
for the final cleanup in step 11.

## 1. What this service is

The Knesset website blocks requests from cloud providers outside Israel, so the
GitHub worker and the Vercel app cannot fetch from it directly. The **fetch
proxy** is a small container that runs in Google Cloud Run in Tel Aviv
(`me-west1`) and makes those requests from inside Israel.

It does one job and holds no secrets other than its own access token. It has no
database, email, AI model, or GitHub credentials.

| Item | Value |
| --- | --- |
| Code | `cloud/knesset_feed/` (`app.py`, `Dockerfile`, `cloudbuild.yaml`) |
| Cloud Run service name | `knesset-feed` |
| Artifact Registry repository | `knesset-feed` (Docker format) |
| Region | `me-west1` (Tel Aviv). Do not change it. Other regions are blocked. |
| Container port | `8080` |
| Endpoints | `GET /feed`, `GET /approvals`, `GET /pdf?url=...` |
| Authentication | Header `Authorization: Bearer <KNESSET_FETCH_TOKEN>` |

Who calls it:

- **GitHub Actions** (`letters.yml`, `always_send.yml`) is the scheduled worker.
- **Vercel** (the web app) uses it for the manual "refresh" button.

Both read two settings: `KNESSET_FETCH_URL` (the service address) and
`KNESSET_FETCH_TOKEN` (the password). A move means standing up a new copy, then
pointing those two settings at it.

> The Neon database, Neon Auth (`auth_proxy.py`), and the email provider are
> separate. They do not move with this service and need no changes.

## 2. Before you start

You need:

- The new Google account, with a **billing account** it can use. Cloud Run needs
  billing enabled even though usage is usually inside the free allowance.
- The [`gcloud` CLI](https://cloud.google.com/sdk/docs/install) installed.
- A clone of this repository.
- Admin access to the GitHub repository and the production Vercel project.

The new project already exists in the new account (named "Moni"):

- Project ID: `moni-510609`
- Project number: `998754133296`

Every command below uses the project ID. The project number appears in the
Cloud Run service URL, so the new service should be at
`https://knesset-feed-998754133296.me-west1.run.app`.

Sign in and set the defaults for the rest of the session:

```sh
gcloud auth login NEW_ACCOUNT@gmail.com
export PROJECT=moni-510609
export REGION=me-west1
```

## 3. Confirm the project and turn on billing

```sh
gcloud projects describe $PROJECT                 # projectNumber should be 998754133296
gcloud billing accounts list                      # copy the ACCOUNT_ID
gcloud billing projects link $PROJECT --billing-account=ACCOUNT_ID
```

If `describe` fails, you are signed in to the wrong account or the project is
not in this account. If billing is already linked, the last command is harmless.

## 4. Enable the APIs and create the image repository

```sh
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com --project=$PROJECT

gcloud artifacts repositories create knesset-feed \
  --project=$PROJECT --location=$REGION --repository-format=docker
```

## 5. Create the build service account

A dedicated account named `knesset-build` runs the build. It is separate from
the account that runs the service.

```sh
gcloud iam service-accounts create knesset-build --project=$PROJECT

BUILDER=knesset-build@$PROJECT.iam.gserviceaccount.com

# Write images to the repository
gcloud artifacts repositories add-iam-policy-binding knesset-feed \
  --project=$PROJECT --location=$REGION \
  --member="serviceAccount:$BUILDER" --role=roles/artifactregistry.writer

# Write build logs
gcloud projects add-iam-policy-binding $PROJECT \
  --member="serviceAccount:$BUILDER" --role=roles/logging.logWriter
```

Cloud Build also needs to read the uploaded source. Cloud Build stages it in a
Cloud Storage bucket named `moni-510609_cloudbuild`, which is created by the first
build. If the first build fails with a storage permission error, grant the
builder `roles/storage.objectViewer` on that bucket and retry.

The service that runs the container (the runtime account) needs no roles. Leave
it with the default settings.

## 6. Create the access token

Generate a fresh random token. Do **not** reuse the old one. Never paste it into
a command line, a file in the repository, or a chat.

```sh
umask 077
printf 'KNESSET_FETCH_TOKEN: "%s"\n' "$(openssl rand -hex 32)" > ./knesset-fetch-env.yaml
```

This creates a private file (mode 600) in your current folder. Keep it outside
the repository (or confirm it is ignored by git). You will use it for the deploy
in step 8 and read it again in step 10. Delete it when you are finished.

## 7. Build the container image

Run this from the **repository root** (the folder that contains `cloud/`):

```sh
gcloud builds submit --project=$PROJECT --region=$REGION \
  --service-account=projects/$PROJECT/serviceAccounts/$BUILDER \
  --config=cloud/knesset_feed/cloudbuild.yaml .
```

When it finishes, note the `BUILD_ID` it prints. The image is:

```text
me-west1-docker.pkg.dev/moni-510609/knesset-feed/service:BUILD_ID
```

The `.gcloudignore` file limits what is uploaded to the service code. No `.env`,
database, email, or client files are sent.

## 8. Deploy to Cloud Run

```sh
gcloud run deploy knesset-feed --project=$PROJECT --region=$REGION \
  --image=me-west1-docker.pkg.dev/$PROJECT/knesset-feed/service:BUILD_ID \
  --port=8080 --cpu=1 --memory=512Mi --min=0 --max=1 \
  --concurrency=4 --timeout=300 --allow-unauthenticated \
  --env-vars-file=./knesset-fetch-env.yaml
```

Why these settings:

- `--allow-unauthenticated` lets the request reach the container. The app itself
  rejects any request without the correct bearer token.
- `--min=0` means it costs nothing while idle. `--max=1` caps cost.
- `--timeout=300` must stay at 300 seconds. The `/approvals` call can take
  up to 200 seconds.

The command prints a **Service URL** such as
`https://knesset-feed-123456789.me-west1.run.app`. This is your new
`KNESSET_FETCH_URL`. If you can't see it, run:

```sh
gcloud run services describe knesset-feed --project=$PROJECT --region=$REGION \
  --format='value(status.url)'
```

If you prefer Google-managed secret storage over the env file, put the token in
Secret Manager, grant the runtime service account
`roles/secretmanager.secretAccessor`, and deploy with `--set-secrets` instead of
`--env-vars-file`. The result is the same for the app.

## 9. Test the new service before changing anything else

Load the token into your shell without printing it, then test:

```sh
TOKEN=$(sed -n 's/^KNESSET_FETCH_TOKEN: "\(.*\)"$/\1/p' ./knesset-fetch-env.yaml)
URL=https://YOUR-NEW-SERVICE-URL

curl -s -o /dev/null -w '%{http_code}\n' "$URL/feed"                      # expect 401
curl -s -H "Authorization: Bearer $TOKEN" "$URL/feed" | head -c 300      # expect JSON
curl -s -H "Authorization: Bearer $TOKEN" "$URL/approvals" | head -c 300 # expect JSON
```

Also test one PDF: take a PDF link from the `/feed` output (it must be under
`https://fs.knesset.gov.il/globaldocs/FINANCE/`), URL-encode it, and request
`$URL/pdf?url=<encoded>` with the same header. Expect a valid PDF.

Do not continue until all four checks behave as described. Do **not** start the
GitHub email workflows as a test. They can send real email and cost money for
model usage.

## 10. Switch the callers to the new service

Do both places. Use the **new** URL and the **new** token.

**GitHub** (repository settings, Secrets and variables, Actions):

- Variable `KNESSET_FETCH_URL` = the new service URL, with no trailing path.
- Secret `KNESSET_FETCH_TOKEN` = the new token.

**Vercel** (production project, Settings, Environment Variables):

- `KNESSET_FETCH_URL` = the new service URL.
- `KNESSET_FETCH_TOKEN` = the new token.
- Then **redeploy** the project. Vercel only reads changed variables on a new
  deployment.

Then confirm:

1. In the production app, press the manual feed refresh. It should succeed.
2. Wait for the next scheduled worker run in GitHub Actions and check that it
   finishes green.

If either fails, set `KNESSET_FETCH_URL` and `KNESSET_FETCH_TOKEN` back to the
old values and redeploy Vercel. The old service keeps working until you delete it.

## 11. Clean up

1. Delete the local token file: `rm ./knesset-fetch-env.yaml`
2. Once both callers have worked with the new service for a few days, delete the
   old Cloud Run service, or the old project, from the old account. Deleting a
   project removes everything in it, so check first that nothing else lives
   there.
3. Check the new billing account for a budget alert and review usage after the
   first week. The free allowance is not a spending cap. Container image
   storage, builds, and network transfer can still cost money.

## 12. Quick reference

Settings to carry over exactly:

- Region `me-west1`; service and repository both named `knesset-feed`
- Port `8080`; 1 vCPU; 512 MiB; min 0, max 1 instance; concurrency 4; timeout 300 s
- Public at the Google layer, protected by the bearer token in the app
- Runtime account has no roles; build account is `knesset-build`

Settings that change:

- Project ID, service URL, and `KNESSET_FETCH_TOKEN` (always generate a new one)

Not needed: static IP, VPC connector, NAT gateway, Cloud Scheduler.

Troubleshooting:

| Symptom | Likely cause |
| --- | --- |
| Build fails with a permission error | Missing role from step 5, or APIs not yet enabled |
| `/feed` returns 401 with the token | Token in the env file differs from the one you sent |
| `/feed` or `/pdf` times out or is refused by Knesset | Service is not in `me-west1` |
| Web app still uses the old service | Vercel was not redeployed after the variable change |
| Worker fails but the web app works | GitHub variable or secret not updated |
