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
