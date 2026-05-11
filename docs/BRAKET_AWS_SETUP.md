# AWS Braket Setup — Prerequisites and Cost Guardrails

This document covers everything needed before running real D-Wave QPU jobs via Amazon Braket.
All configuration maps directly to `services/braket_backend.py` and `.env.example`.

---

## 1. AWS account and service activation

1. **Dedicated AWS account** (recommended) or a sub-account with a distinct billing alert.
2. Enable **Amazon Braket** in the AWS console:
   - Console → Amazon Braket → Get started → Enable Braket in your region.
   - Default region used by the codebase: `us-east-1` (`BraketConfig.aws_region`).
   - D-Wave Advantage devices are available in `us-east-1` — do not change the region unless you verify device availability.
3. Accept the **Braket service terms** in the console before submitting any tasks.

---

## 2. IAM — minimum required permissions

Create an IAM user or role with the following policy (or the managed `AmazonBraketFullAccess`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "braket:GetDevice",
        "braket:GetQuantumTask",
        "braket:CreateQuantumTask",
        "braket:CancelQuantumTask",
        "braket:ListQuantumTasks",
        "braket:SearchQuantumTasks"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:GetBucketLocation",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::YOUR_BUCKET_NAME",
        "arn:aws:s3:::YOUR_BUCKET_NAME/*"
      ]
    }
  ]
}
```

Replace `YOUR_BUCKET_NAME` with the value you set in `BRAKET_S3_BUCKET`.

---

## 3. S3 bucket for results

Braket writes task output to S3. Create a dedicated bucket:

```bash
aws s3 mb s3://YOUR_BUCKET_NAME --region us-east-1
```

- Set `BRAKET_S3_BUCKET=YOUR_BUCKET_NAME` in your `.env`.
- The codebase writes to the `braket-results/` prefix inside that bucket
  (see `_execute_braket` in `services/braket_backend.py`).
- Enable **versioning** and a lifecycle rule to expire objects after 90 days
  (raw result JSON can be large for high-shot runs).

---

## 4. AWS credentials

Options (in order of preference for production):

| Method | How |
|--------|-----|
| EC2/ECS instance profile | Attach IAM role; no credentials in env |
| AWS SSO / IAM Identity Center | `aws configure sso` |
| Long-lived access keys (dev only) | `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` in `.env` |

The boto3 session in `BraketAnnealingOptimizer._initialize_braket` uses
`boto3.Session(region_name=self.config.aws_region)`, which inherits the
standard credential chain automatically.

---

## 5. D-Wave device ARN

Available D-Wave QPU device ARNs on Braket (verify current availability in the Braket console):

| Device | ARN |
|--------|-----|
| D-Wave Advantage_system6.4 | `arn:aws:braket:us-east-1::device/qpu/d-wave/Advantage_system6` |
| D-Wave Advantage_system4.1 | `arn:aws:braket:us-east-1::device/qpu/d-wave/Advantage_system4` |
| D-Wave 2000Q_6 | `arn:aws:braket:us-east-1::device/qpu/d-wave/DW_2000Q_6` |

Set in `.env`:

```bash
BRAKET_DEVICE_ARN=arn:aws:braket:us-east-1::device/qpu/d-wave/Advantage_system6
```

> **Tip:** Run `aws braket get-device --device-arn ARN` to confirm the device is `ONLINE`
> before submitting. D-Wave QPUs have maintenance windows; check the Braket console calendar.

---

## 6. Problem size limits (D-Wave topology)

| Device | Physical qubits | Practical QUBO limit (after embedding) |
|--------|-----------------|----------------------------------------|
| Advantage_system6 | ~5,000 | ~180 binary variables (dense), more for sparse |
| Advantage_system4 | ~5,000 | similar |
| DW_2000Q | ~2,000 | ~60–90 binary variables (dense) |

The `_execute_braket` implementation uses a simplified qubit mapping with a
hard cap of 100 (`qubit_map = {i: i for i in range(min(n, 100))}`). This
means it does **not** perform minor-embedding. For a validation run:

- Keep `n` (number of assets) at **5–10** to stay well within the fully-connected
  subgraph that D-Wave can handle without embedding.
- For larger `n`, minor-embedding via the `dwave-networkx` library would be required.
  This is tracked as a future enhancement.

---

## 7. Environment variables — complete reference

Add to your `.env` for real-device runs (do not commit):

```bash
BRAKET_ENABLED=true
BRAKET_USE_MOCK=false
BRAKET_DEVICE_ARN=arn:aws:braket:us-east-1::device/qpu/d-wave/Advantage_system6
BRAKET_S3_BUCKET=your-bucket-name-for-results
BRAKET_AWS_REGION=us-east-1
BRAKET_SHOTS=100
BRAKET_TIMEOUT=300

# AWS credentials (only if not using instance profile / SSO)
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
```

---

## 8. Cost guardrails

| Item | Typical cost (2026) | Mitigation |
|------|----------------------|------------|
| D-Wave QPU task | ~$0.00019/shot on Advantage | Use `BRAKET_SHOTS=100` for validation (≈$0.02/run) |
| S3 storage | < $0.01/month for result JSON | Lifecycle expiry rule |
| S3 PUT requests | < $0.01/day at dev cadence | Acceptable |

Set a **AWS Billing Alert** at $10/month and a **Braket budget** in AWS Cost Explorer
before running any QPU tasks.

**Do not** increase `BRAKET_SHOTS` beyond 1000 without understanding the cost impact
($0.19/run at 1000 shots on D-Wave).

---

## 9. Verifying setup before first real run

```bash
# 1. Confirm AWS credentials work
aws braket get-device \
  --device-arn arn:aws:braket:us-east-1::device/qpu/d-wave/Advantage_system6 \
  --region us-east-1 \
  | python -m json.tool | grep -E '"status"|"name"'

# 2. Confirm SDK is installed
python -c "import braket; print('Braket SDK:', braket.__version__)"

# 3. Confirm S3 bucket is accessible
aws s3 ls s3://YOUR_BUCKET_NAME --region us-east-1

# 4. Run the validation script in mock mode first
BRAKET_ENABLED=true BRAKET_USE_MOCK=true \
  python scripts/braket_validate.py --n 5 --seed 42

# 5. Run the validation script against the real device
BRAKET_ENABLED=true BRAKET_USE_MOCK=false \
  BRAKET_DEVICE_ARN=arn:aws:braket:us-east-1::device/qpu/d-wave/Advantage_system6 \
  BRAKET_S3_BUCKET=your-bucket-name-for-results \
  python scripts/braket_validate.py --n 5 --seed 42 --output artifacts/braket_run_$(date +%Y%m%d).json
```

The validation script (`scripts/braket_validate.py`) captures the task ARN/ID,
timing, backend metadata, and portfolio weights in a machine-readable JSON artifact.

---

## 10. Related files

| File | Purpose |
|------|---------|
| `services/braket_backend.py` | `BraketAnnealingOptimizer` — core hardware dispatch |
| `services/portfolio_optimizer.py` | Routes `braket_annealing` objective to Braket backend |
| `services/tenant_integrations.py` | `save_braket_metadata` / `load_braket_metadata` (per-tenant DB) |
| `.env.example` | All `BRAKET_*` environment variable defaults |
| `scripts/braket_validate.py` | End-to-end validation script (mock → real device) |
| `tests/test_braket_real_device.py` | Pytest-based unit and integration tests |

---

*Last updated: April 2026*
