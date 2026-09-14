# California Housing Market — setup and operations

This repository contains a React dashboard, a read-only Python API, the existing cleaning pipeline adapted for scheduled ingestion, and AWS templates. Start locally with synthetic data. AWS deployment and a real CRMLS reconciliation require your account configuration and data access; neither is performed by installing this repository.

## 1. Run the dashboard locally

Requirements: Python 3.13, Node 22, and Docker Desktop (running). From the repository root:

```sh
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
docker compose up -d
export DATABASE_URL='postgresql://idx:local-development-only@127.0.0.1:55432/housing'
python -m backend.seed_demo
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```sh
npm ci --prefix web
npm run dev --prefix web
```

Open http://127.0.0.1:5173. Every synthetic publication carries a conspicuous demonstration banner, including fictitious agent and brokerage rankings. The production ingestion command never sets this flag. Do not seed a production database. A running PostgreSQL installation can replace Docker; set `DATABASE_URL` to its local database.

For tests, create a **separate disposable database** and set `TEST_DATABASE_URL`; database tests drop and recreate its `market` schema. Run `python -m unittest discover -s tests -v`, `npm run build --prefix web`, and `npm test --prefix web`. Install Chromium first with `cd web && npx playwright install chromium`. Browser tests expect the API and synthetic publication above. CI uses PostgreSQL 17 and synthetic fixtures; no Trestle credentials are available to pull requests.

## 2. Check AWS billing before provisioning

Choose **Oregon (`us-west-2`)** throughout. In Billing → Free Tier, check your account's plan, credit balance and expiration. Eligibility depends on the account creation date and plan; RDS is not permanently free. The foundation creates a **$40 monthly cost budget** with actual-spend email alerts at $20, $30 and $40. Budgets notify; they do not stop resources or cap charges. See [RDS Free Tier](https://aws.amazon.com/rds/free/).

Use **$20–40/month only as an initial low-traffic planning range**, excluding Trestle/MLS subscriptions and a domain. Obtain a current `us-west-2` estimate in the [AWS Pricing Calculator](https://calculator.aws/) before deployment: include 730 instance-hours of Single-AZ `db.t4g.micro`, 20 GB gp3, excess backups/snapshots, Secrets Manager, S3 full-history exports each month, CloudFront, HTTP API, Lambda, CloudWatch and Fargate. For Fargate estimate `2 × job hours` vCPU-hours plus `16 × job hours` GB-hours, temporary public IPv4 and retries. Profile the initial full extraction to determine job hours and disk/memory needs. The rolling cap limits live records, **not provisioned RDS storage charges**. Archives and retained backups continue to cost money. References: [RDS pricing](https://aws.amazon.com/rds/postgresql/pricing/), [Fargate pricing](https://aws.amazon.com/fargate/pricing/).

## 3. Install tools and sign in

Install [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html), [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html), Docker, Python and Node. Prefer `aws configure sso` and `aws sso login` using an administrator-approved permission set. Export `AWS_PROFILE` if using a named profile and `AWS_DEFAULT_REGION=us-west-2`. Verify the account with `aws sts get-caller-identity`. Never commit access keys, `.env`, exported credentials or source records.

Deploy the foundation from the root, replacing the email:

```sh
aws cloudformation deploy --template-file infra/foundation.yaml \
  --stack-name housing-foundation --parameter-overrides AlertEmail=you@example.com
aws cloudformation describe-stacks --stack-name housing-foundation \
  --query 'Stacks[0].Outputs' --output table
```

Confirm the SNS subscription email. The stack creates one public subnet and two private subnets, an internet gateway, private versioned buckets, ECR, four secrets, and **PostgreSQL 17.11 / Single-AZ / db.t4g.micro / 20 GB encrypted gp3 / seven-day automated backups**. RDS is private and deletion-protected. Only the API and ingestion security groups may reach port 5432. The API has no general internet route. Ingestion runs with a public IP and no inbound permissions, accessing RDS by private address; there is no NAT gateway. See [Fargate networking](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-tasks-services.html).

If AWS no longer permits creating the pinned minor version, verify an available PostgreSQL 17 minor version in the RDS console, update `EngineVersion`, and validate the template before deploying. Do not silently switch database major versions.

## 4. Configure secrets and private reference data

In Secrets Manager, open the foundation's `TrestleSecretArn` and replace its placeholders with your existing `CORELOGIC_API_URL` and `AUTH_ENDPOINT` values. The extractor supports the existing authentication proxy contract; it does not substitute a different OAuth integration. Preserve the JSON keys. No secret belongs in GitHub or the browser.

Find the `ArchiveBucket` output. Upload the **existing pipeline reference files** under these exact private keys:

```text
references/california_valid_zip_codes.csv
references/City_and_County_Boundaries.geojson
references/coordinate_overrides.csv              (optional)
```

Use the S3 console or `aws s3 cp` with your local file paths. These are cleaning inputs; they are separate from the simplified public Census map boundaries in `web/public/geo`. Optional overrides require `ListingKey,Latitude,Longitude,reason,source`, one row per listing; they fill missing coordinates only. Existing manual cleaning corrections remain in `clean.py`. Do not upload old `_filled` exports as replacement monthly inputs: their stale transaction fields must not overwrite refreshed Trestle values.

The database admin, ingestion and application passwords are generated separately. Bootstrap creates `etl_writer` and `api_reader` roles. The API credential is resolved from Secrets Manager into Lambda's encrypted configuration at deployment; Lambda does not require a NAT gateway to retrieve it at runtime. For rotation, update the secret, run the bootstrap task to update the PostgreSQL role, then redeploy with an incremented `--credential-revision`. Coordinate a short maintenance window because secret and database password updates are not simultaneous. Never enable automatic secret rotation without implementing this coordinated process.

## 5. Publish the image and deploy the application

Use a unique release identifier; ECR tags are immutable. Read `RepositoryUri` from foundation outputs, then:

```sh
export PIPELINE_REPOSITORY='YOUR_REPOSITORY_URI'
export RELEASE_ID="$(git rev-parse --short HEAD)-initial"
aws ecr get-login-password --region us-west-2 | \
  docker login --username AWS --password-stdin "${PIPELINE_REPOSITORY%%/*}"
docker build --platform linux/amd64 -t "$PIPELINE_REPOSITORY:$RELEASE_ID" .
docker push "$PIPELINE_REPOSITORY:$RELEASE_ID"
python -m scripts.aws_release --image "$PIPELINE_REPOSITORY:$RELEASE_ID" \
  --release "$RELEASE_ID" --schedule DISABLED
```

`aws_release` reads foundation outputs, builds Lambda in a Linux SAM container, deploys `housing-app`, uploads the frontend, saves the release's index, and invalidates changed CloudFront paths. Docker must be running. A deployment creates roles, Lambda, API Gateway, ECS task definitions, monitoring and CloudFront. The default HTTPS CloudFront hostname is the initial site address. It may show “market data unavailable” until initialization finishes. Both the ingestion and freshness schedules remain disabled at this stage.

CloudFront uses origin access control for private S3 and sends `/api/*` to HTTP API. API cache keys include all query parameters, including dataset version; maximum shared-cache age is five minutes. The website calls same-origin APIs. The OpenAPI contract is at `/api/openapi.json`; for the interactive Swagger viewer use the local API at http://127.0.0.1:8000/api/docs (the deployed content security policy intentionally does not allow third-party Swagger assets). See [CloudFront origin access control](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html).

## 6. Initialize and validate the real dataset

```sh
python -m scripts.aws_task migrate
python -m scripts.aws_task ingest
```

These launch temporary tasks in the public subnet, with private RDS access. The ingestion task has 2 vCPU, 16 GB memory and 20 GB temporary storage. Task IDs and the CloudWatch log-group output identify progress. The helper waits up to four hours; if the monitor times out the task continues, so inspect ECS before dispatching again. The job itself holds a database advisory lock to prevent overlapping publications.

Ingestion validates monthly listing/sold pairs, extracts all history from January 2024 to the previous completed month, archives each completed export privately under `runs/<run-id>/`, transforms the full history and publishes only the eligible window. Check `quality.json`, container exit code, `/api/v1/meta`, monthly counts, and a selection of counties/ZIPs/property types against independent calculations. Reconcile source totals before treating the dashboard as production. A successful exit alone does not certify CRMLS coverage or Tableau parity. See [ANALYTICS.md](ANALYTICS.md) for definitions and known differences.

Migrations are deliberately separate from web deployment. Review and run additive schema migrations before an application release that requires them. Avoid dropping columns until all retained application releases no longer use them.

## 7. Enable the monthly refresh

After initialization and reconciliation, repeat the release command with `--schedule ENABLED`. The application template schedules **06:00 America/Los_Angeles on day 7**; EventBridge Scheduler handles daylight saving time. The job derives the previous complete month from Pacific time. It re-extracts full history on each new run, allowing corrections and removals to propagate. See [scheduled ECS tasks](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/tasks-scheduled-eventbridge-scheduler.html).

| Publication | RDS reporting months |
|---|---|
| September 7, 2026 | January 2024–August 2026 |
| January 7, 2027 | January 2024–December 2026 |
| February 7, 2027 | February 2024–January 2027 |

The staging load, validation, active-version switch and retention deletion share one database transaction. Listing records use listing-contract month; sold records use close month, including sales whose original listing predates the window. One previous version is retained and trimmed to the new boundary; other versions are removed. Failed refreshes preserve the published dataset. Backups and private raw archives have independent retention and are not erased by the 36-month market-data policy.

Alerts cover dispatch dead letters, failed container exits, task startup failures, and a day-8 freshness check. Confirm delivery with a controlled test in a test environment. Check CloudWatch after the first scheduled run. Scheduler retries cover dispatch failures; an accepted task that later fails requires inspection and a deliberate retry.

## 8. Connect GitHub Actions through OIDC

`Validate` runs Python/PostgreSQL tests, template validation, frontend contract generation/build and desktop/mobile browser tests. `Deploy` waits for those checks on main, then uses short-lived OIDC credentials. It remains inactive until repository variable `AWS_DEPLOY_ROLE_ARN` is set. No database migration runs automatically.

1. In IAM, add the identity provider `https://token.actions.githubusercontent.com`, audience `sts.amazonaws.com` (reuse it if present).
2. Create a role trusting that provider for the exact repository and **production environment**, with audience `sts.amazonaws.com`. For legacy subject formatting the `sub` is `repo:trenton-pham/idx-exchange:environment:production`. Newer repositories may include immutable owner/repository IDs; verify the repository's actual subject format. Never use a repository-wide wildcard. Follow [GitHub's AWS OIDC guide](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws).
3. Have an AWS administrator scope deployment permissions to the `housing-app` stack and its resources: CloudFormation change sets, SAM artifact bucket, ECR image push, web bucket writes, CloudFront invalidation, Lambda/API/ECS/Scheduler/CloudWatch updates, Secrets Manager reads for dynamic references, and creation/passing of this stack's execution roles. Foundation provisioning, database deletion and raw archive access are not CI responsibilities. Use a dedicated CloudFormation service role in accounts requiring centralized privilege control. `infra/deploy-policy.example.json` lists the action groups to scope with your concrete resource ARNs; it is a review worksheet, not an attachable all-resources policy.
4. In GitHub Settings → Environments, create `production`, restrict deployment branches to main, and optionally require a reviewer. Add repository variable `AWS_DEPLOY_ROLE_ARN`. Optional variables: `FOUNDATION_STACK`, `APPLICATION_STACK`, `CREDENTIAL_REVISION`; set `SCHEDULE_STATE=ENABLED` **only after step 7** so later CI deployments preserve that choice.
5. Protect main with the `Validate` check. Review/pin action versions to commit SHAs under your repository policy. Push a reviewed release. Verify the workflow, resulting site and data-version metadata.

## 9. Retry, rollback, restore and teardown

- **Interrupted extraction:** find the original UUID and month in CloudWatch. Run `python -m scripts.aws_task ingest --run-id UUID --end-month YYYY-MM`. This reuses that run's completed immutable exports from S3; partial exports were never archived. For a fresh source snapshot, omit the UUID. Never mix exports between runs. Source revisions are ordered by authoritative identity and modification timestamp; unresolved conflicts block publication.
- **Dataset rollback:** `python -m scripts.aws_task rollback`. This activates the previous successful dataset within its trimmed reporting boundary. It cannot bring expired records back into RDS. Invalidate `/api/*` on CloudFront and reload; clients otherwise converge within five minutes. Pause scheduling during incident investigation.
- **Application rollback:** redeploy the prior Git commit/ECR image with its release ID. Prior hashed assets and `releases/<release>/index.html` remain in the private web bucket; copying that index to `index.html` and invalidating `/` and `/index.html` rolls back the website alone. Keep compatible Lambda and database schemas. ECR retains ten images, so record a durable release if it must outlive that policy.
- **Restore RDS:** in RDS → Automated backups choose point-in-time restore into a **new private instance**, using the same subnet group and application-only security groups. Validate it in isolation, update the application database-host parameter, redeploy and test. Backups retain seven days; manual snapshots persist until explicitly deleted. Restore may contain older market rows: republish/trim to the required window before serving publicly.
- **Monitor growth:** inspect database free storage, job memory/disk and extraction duration monthly. Full-history archives grow even though RDS keeps 36 months. Do not set a deletion lifecycle for raw archives unless you choose to change the archival policy.
- **Teardown:** disable schedules, stop running tasks, export any required records, and take a final snapshot. Delete `housing-app`. Disable RDS deletion protection only when you intend to delete it, then delete `housing-foundation`. RDS snapshot deletion policies and retained buckets/secrets can leave billable resources. Review CloudFormation retained resources, empty versioned buckets including noncurrent versions only after reviewing their contents, and delete unneeded snapshots/ECR images/secrets manually. Do not expect deleting the website to stop RDS costs.

## Release boundaries

This release covers monthly available CRMLS residential data, public aggregates and permitted listing-side named rankings. It has no accounts, property detail pages, forecasting or transaction editing. A local synthetic performance check does not establish production RDS latency. Confirm the two-second warm-response target and API payload sizes on the actual feed before public launch; initial API concurrency is five, one bounded connection per request, with eight-second SQL timeouts.
