# Roadmap

## 1. Account and deployment safety

- [ ] Create a small AWS Budget and billing alert in the target account.
- [ ] Confirm Bedrock model access, region, and model/inference-profile ID.
- [ ] Install development requirements and run the existing unit tests.
- [ ] Review the Terraform plan, especially IAM and the region, before applying.
- [ ] Confirm the SNS email subscription.
- [ ] Backfill history and verify the collector, detector, and email path in CloudWatch.
- [ ] Check the billing dashboard after the first end-to-end run.

## 2. Validate report-only remediation

- [ ] In a disposable account, create one low-usage test instance and one with `protected=true`.
- [ ] Run with `dry_run=true`; confirm the first is reported and the protected instance is absent.
- [ ] Review audit-table records and SNS output.
- [ ] Only in the disposable account, consider stopping the test instance with `dry_run=false`.
- [ ] Keep `allow_delete=false` unless specifically testing with disposable EBS/EIP resources.

## 3. Production-quality engineering

- [ ] Split IAM roles and policies by Lambda responsibility; scope Bedrock to the selected model.
- [ ] Add CloudWatch alarms and failure handling (timeouts, retries, dead-letter queue).
- [ ] Add idempotency and structured logs/metrics for repeated invocations.
- [ ] Require an explicit opt-in tag for any resource eligible for remediation.
- [ ] Add a read-only dashboard/API for cost history and audit findings.
- [ ] Add a remote Terraform backend with encryption, versioning, and locking.
- [ ] Add GitHub Actions deployment through OIDC with an approval gate; do not use long-lived keys.
- [ ] Add AWS-mocked handler tests and integration instructions for a disposable account.
- [ ] Add a diagram export, sample sanitized alert, and short demo recording.

## 4. Portfolio presentation

- [ ] Explain threshold choices and known limitations of a short moving average.
- [ ] Document actual account/region-specific costs from a controlled test deployment.
- [ ] Show one successful anomaly, one no-anomaly day, and one protected-resource case.
- [ ] Include teardown evidence and note that Bedrock output is advisory, not authoritative.
