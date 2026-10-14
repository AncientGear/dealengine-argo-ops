# Backend runtime prerequisites

Argo is the sole backend workload owner. This chart consumes the existing
`backend-runtime` Secret; it does not create a Secret or manage ESO resources.

Before any Argo sync:

1. Seed the AWS Secrets Manager application secret `dev/dealengine/backend-runtime`
   outside Terraform and Git with JSON fields `DATABASE_URL` and `TOKEN_SECRET`.
   Initial seeding and later rotation are operator-owned prerequisites, not
   automated by this chart. Never put values in manifests, CLI arguments or logs.
2. Set `DATABASE_URL` to the real RDS endpoint hostname on port `5432`, not an
   IP address, localhost or tunnel hostname. Require `sslmode=verify-full` and
   `sslrootcert=/etc/rds-ca/us-east-2-bundle.pem`. Placeholder-only shape:
   `postgresql://<URL-encoded-user>:<URL-encoded-password>@<real-RDS-hostname>:5432/<database>?sslmode=verify-full&sslrootcert=/etc/rds-ca/us-east-2-bundle.pem`.
3. Verify the ExternalSecret is Ready and `backend-runtime` exists in
   `backend-dev` with both required keys, without displaying their values.
4. Verify remote Git `main` contains the tested ARM image digest before allowing
   Argo to sync. A local values change is not publication; do not sync the old
   remote AMD64 digest.

Kubernetes Secret-backed environment variables do not refresh in running pods.
After rotation and successful ESO reconciliation, arrange an operator-authorized
backend pod restart through the existing Argo workflow.

## Public RDS trust bundle

Dev enables `rdsCa.enabled`; other environments default to disabled. The chart
mounts the public CA bundle read-only at `/etc/rds-ca/us-east-2-bundle.pem`.
Source: https://truststore.pki.rds.amazonaws.com/us-east-2/us-east-2-bundle.pem
(AWS RDS regional truststore, retrieved with HTTPS certificate verification).
For CA updates, retrieve that official source with TLS verification enabled,
review the public PEM change, and publish through the normal Argo Git workflow.
This CA mount supports TLS verification; it does not prove live database access,
secret readiness or deployment readiness.

## Manual backend rollback in dev

Rollback changes the desired image digest in GitOps through a pull request.
It does not rebuild the image, rewrite Git history or restore database data.

### Preconditions

- Verify the candidate digest still exists in ECR.
- Verify compatibility with the node architecture, runtime configuration,
   database schema and TLS requirements.
- Record the current healthy digest and the reason for rollback.
- Do not use the historical AMD64 image on the current ARM64 dev node.
- Coordinate deployments and rollback with the operator.

### Procedure

1. Create a rollback branch from an up-to-date `main`.
2. Change only `image.digest` in `environments/dev/values.yaml`.
   Preserve the repository, runtime Secret, RDS CA mount, routing and
   readiness configuration.
3. Run the offline checks below and review the diff.
4. Open a PR against `main`, recording the previous and candidate digests,
   compatibility evidence and check results.
5. Review and merge the PR before syncing Argo.
6. Verify remote `main` contains the intended digest.
7. Perform an explicitly authorized manual sync of `backend-dev`.
   Auto-sync is not configured in the currently verified Application.
8. Verify Argo synchronization and health, the Deployment image,
   pod readiness, ALB target health and the public API.

Do not use `kubectl rollout undo` as the permanent recovery mechanism:
it does not update the desired state in Git.

If recovery fails, stop and diagnose. Returning to the recorded digest
requires another reviewed GitOps change and an authorized sync.

### Offline checks

Run from the `argo-ops` repository:

      helm lint charts/backend -f environments/dev/values.yaml
      helm template backend charts/backend --namespace backend-dev -f environments/dev/values.yaml > /dev/null
      python3 charts/backend/tests/test_rds_ca.py -v
      python3 charts/backend/tests/test_targetgroup_configuration.py -v
      git diff --check

These checks do not prove image compatibility, live database access or
successful recovery. A real rollback test requires a compatible release.