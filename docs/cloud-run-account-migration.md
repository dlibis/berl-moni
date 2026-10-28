# Move the Knesset fetch service to another Google account

The service is a regional Cloud Run container in `me-west1` (Tel Aviv), in
project `berl-moni-fetch-20261026`. The project owns the service, registry,
build configuration, and service accounts; a Google account is an IAM identity
that can be granted access to those resources.

## Choose the move

**Only changing who manages it:** add the new account to the existing project.
This keeps the Cloud Run URL and requires no application or caller changes.
This is the easiest and safest option.

**Moving it into a different project:** deploy a second copy there, verify it,
switch callers, then retire the old copy. Cloud Run services cannot be moved
between projects in place. The new URL and a new auth token must be configured
in GitHub Actions and Vercel.

## Option A: grant the new account access to the existing project

An existing project Owner can run this, replacing the email:

```sh
gcloud projects add-iam-policy-binding berl-moni-fetch-20261026 \
  --member='user:NEW_ACCOUNT@gmail.com' --role='roles/owner'
```

Owner is broad access. For a narrower setup, grant `roles/run.admin`,
`roles/artifactregistry.admin`, and `roles/cloudbuild.builds.editor` on the
project, plus `roles/iam.serviceAccountUser` on the `knesset-build` service
account. The new account also needs permission to use the project’s billing
account for future billable changes. Confirm access with:

```sh
gcloud auth login NEW_ACCOUNT@gmail.com
gcloud config set project berl-moni-fetch-20261026
gcloud run services describe knesset-feed --region=me-west1
```

Keep the existing project and GitHub/Vercel configuration in place.

## Option B: recreate it in a new project

Use a new project ID below in place of `NEW_PROJECT_ID`; project IDs are
globally unique and cannot be renamed. Link the project to the intended billing
account and grant the deploying account permission to deploy services, create
builds, use service accounts, and write Artifact Registry images. Enable the
required APIs and create the regional image repository:

```sh
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com --project=NEW_PROJECT_ID
gcloud artifacts repositories create knesset-feed \
  --project=NEW_PROJECT_ID --location=me-west1 \
  --repository-format=docker
```

Create a dedicated Cloud Build service account named `knesset-build`. Give it
the permissions needed by the build: read staged source, write images to the
`knesset-feed` Artifact Registry repository, and write build logs. Pass it to
`gcloud builds submit` as shown below. Keep runtime permissions separate: the
Cloud Run runtime account needs no project roles. If project policy requires
explicit runtime service-account creation, create a dedicated account with no
roles and deploy using it.

Generate a fresh random `KNESSET_FETCH_TOKEN`. Set it on the new Cloud Run
service using a protected environment file (mode `600`) or Secret Manager; do
not place the token in a command line, source file, or logs. The application
expects it as the `KNESSET_FETCH_TOKEN` environment variable.

From the repository root, build the image:

```sh
gcloud builds submit --project=NEW_PROJECT_ID --region=me-west1 \
  --service-account=projects/NEW_PROJECT_ID/serviceAccounts/knesset-build@NEW_PROJECT_ID.iam.gserviceaccount.com \
  --config=cloud/knesset_feed/cloudbuild.yaml .
```

Deploy the built image to Cloud Run in `me-west1`, preserving the current
service settings: request-based billing, 1 vCPU, 512 MiB, min 0/max 1
instances, concurrency 4, and 300-second timeout. Configure the new token as
`KNESSET_FETCH_TOKEN`; make the service publicly invokable at the platform
layer because the application itself checks the bearer token. Use the image
URI printed by Cloud Build:

```text
me-west1-docker.pkg.dev/NEW_PROJECT_ID/knesset-feed/service:BUILD_ID
```

With the token stored in a mode-600 YAML file outside the repository (for
example, `./knesset-fetch-env.yaml`), deploy with:

```sh
gcloud run deploy knesset-feed --project=NEW_PROJECT_ID --region=me-west1 \
  --image=me-west1-docker.pkg.dev/NEW_PROJECT_ID/knesset-feed/service:BUILD_ID \
  --port=8080 --cpu=1 --memory=512Mi --min=0 --max=1 \
  --concurrency=4 --timeout=300 --allow-unauthenticated \
  --env-vars-file=./knesset-fetch-env.yaml
```

Delete that temporary file after deploy. A Secret Manager secret is preferable
if you want Google-managed secret storage; grant the runtime account
`roles/secretmanager.secretAccessor` and deploy with `--set-secrets` instead.

The deployer needs permission to act as the selected runtime service account
(`roles/iam.serviceAccountUser`). The returned Cloud Run service URL is the
new `KNESSET_FETCH_URL`.

## Verify and cut over

Before changing callers, check the new service with the same API contract:

- `GET <NEW_URL>/feed` with `Authorization: Bearer <new token>` returns JSON.
- `GET <NEW_URL>/pdf?url=<encoded Knesset PDF URL>` returns a valid PDF.
- Requests without the bearer token return `401`.

Update GitHub repository variable `KNESSET_FETCH_URL` and secret
`KNESSET_FETCH_TOKEN`. Update the same variable and secret in the production
Vercel project, then redeploy Vercel so its runtime uses the new values. Both
GitHub workflows (`letters.yml` and `always_send.yml`) read those repository
settings. Do not dispatch an email workflow as a connectivity test; it can
send real mail.

Verify a production manual feed refresh and a scheduled worker run. Keep the
old service and credentials available until both callers succeed; then remove
the old service/project only if it is no longer needed. Removing a project or
unlinking billing can affect other resources and should be checked separately.

## Configuration to carry forward

- Region: `me-west1` (Tel Aviv)
- Service and Artifact Registry repository: `knesset-feed`
- Container port: `8080`
- Routes: authenticated `GET /feed` and `GET /pdf`
- URL variable: `KNESSET_FETCH_URL`
- Token secret: `KNESSET_FETCH_TOKEN` (rotate when recreating)
- The service fetches only; it has no database, email, model, or GitHub token.
- No static IP, VPC connector, NAT gateway, or separate scheduler is required.

Cloud Run’s free allowance is not a spending cap; billing-account free usage
is shared, and registry storage, builds, and network transfer can still incur
charges. Check the new billing account’s budgets and usage after cutover.
