# Private Knesset fetcher

The fetcher in `moni-510609` requires Google IAM authentication in addition to
the existing application bearer token. Cloud Run checks
`X-Serverless-Authorization: Bearer <Google ID token>`; Flask checks
`Authorization: Bearer <KNESSET_FETCH_TOKEN>`. The Google token's audience is
the configured `KNESSET_FETCH_URL`, without a trailing slash.

The shared Python client uses `google-auth` to exchange external identities for
Google ID tokens. It reuses each token until it approaches expiry, then refreshes
it. Authentication errors fail the request without falling back to token-only
access or exposing provider error details.

## Trust and permissions

Pool: `projects/998754133296/locations/global/workloadIdentityPools/knesset-callers`.

| Caller | Provider | Service account | Restrictions |
| --- | --- | --- | --- |
| GitHub | `github` | `knesset-github@moni-510609.iam.gserviceaccount.com` | Repository ID `1419541086`, owner ID `63005208`, `letters.yml` on `refs/heads/main` |
| Vercel | `vercel` | `knesset-vercel@moni-510609.iam.gserviceaccount.com` | Team ID `team_5cXd8YYNXKUCjgfhBitDcZ8y`, project ID `prj_3c8SljPCk9lxVmlqeKCdGmQHOjST`, production only |

Each external identity has `roles/iam.workloadIdentityUser` on its own caller
account. Each caller account has `roles/run.invoker` on `knesset-feed` only.
Neither caller needs project roles or service-account keys. The runtime account
`knesset-runtime@moni-510609.iam.gserviceaccount.com` has no project roles.
The STS and IAM Credentials APIs must be enabled.

## Caller configuration

Both callers retain `KNESSET_FETCH_URL` and `KNESSET_FETCH_TOKEN` and set
`KNESSET_FETCH_SERVICE_ACCOUNT` to their respective caller account.

GitHub's `KNESSET_FETCH_IDENTITY_PROVIDER` variable points to the pool's `github`
provider. The pinned Google auth action writes refreshable external-account
credentials and exports `GOOGLE_APPLICATION_CREDENTIALS`; the Python client uses
these as its source identity. Do not add a service-account impersonation setting
to that action: the Python client performs the impersonation.

Vercel's `KNESSET_FETCH_IDENTITY_PROVIDER` environment variable points to the
pool's `vercel` provider. Vercel OIDC is enabled with the team issuer
`https://oidc.vercel.com/dlibis-projects` and allowed audience
`https://vercel.com/dlibis-projects`. The web bootstrap reads the OIDC token from
the current function request's `x-vercel-oidc-token` header, never the build's
`VERCEL_OIDC_TOKEN` environment variable. Preview and development deployments
cannot invoke the production fetcher.

Local direct fetching is unchanged when `KNESSET_FETCH_URL` is unset. Calling
the private fetcher locally requires Google application-default credentials
authorized to mint the configured caller's ID token, plus the app token.

## Verification and rollback

Run `letters.yml` manually with `mode=auth-check` to check feed, approvals, and
PDF access without touching the database, calling a model, or sending mail.
Use the signed-in production refresh button to verify the Vercel runtime path.
Requests without a Google identity must receive a Cloud Run 403; a valid Google
identity with no app token must receive a Flask 401.

If federation breaks production, temporarily restore `allUsers` with
`roles/run.invoker` on this service and remove `KNESSET_FETCH_SERVICE_ACCOUNT`
from the affected caller (redeploy Vercel). The application bearer-token check
remains mandatory. This restores token-only access; it also restores exposure
of the container to unauthenticated traffic.
