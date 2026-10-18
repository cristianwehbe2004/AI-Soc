# Use an existing AWS S3 dataset for local ML training

The incident classifier continues to train **locally**. This optional path reads
one existing, analyst-reviewed JSONL object from S3 into memory and feeds the
same training/evaluation gate as a local file. It does not create a bucket,
deploy a server, start SageMaker/Bedrock, enable Security Hub, or upload model
artifacts. No AWS call occurs during the default planning command.

The current project choice is local training with no existing S3 dataset. Keep
using the local JSONL or training-only database commands in
[incident training](incident-training.md). S3 reads remain optional and disabled
unless the execution flag is supplied; no AWS account setup is required now.

## Before making a paid request

1. Check the actual remaining credit and expiration in your AWS Billing console.
   The reported $20 balance is not verified by this repository. An AWS Free Plan
   may restrict available services; a Paid Plan can incur charges after credits
   are exhausted. [AWS Free Tier FAQ](https://aws.amazon.com/free/free-tier-faqs/).
2. Use only an **existing** S3 Standard object containing approved, de-identified
   incident windows. Keep it under 5 MiB by default (the absolute CLI cap is
   20 MiB). S3 storage, requests, and transfer have distinct pricing; do not
   assume every operation is free. [S3 pricing](https://aws.amazon.com/s3/pricing/).
3. Set a zero-spend or low-dollar AWS Budget and monitor Free Tier usage. Budget
   alerts are delayed and are **not a hard spending cap**.
   [AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html),
   [Free Tier usage tracking](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/tracking-free-tier-usage.html).
4. Use short-lived, read-only credentials for the exact account, bucket, and key
   prefix. Never paste keys into the command or commit them. STS identity check,
   S3 `HeadObject`, and S3 `GetObject` are the only AWS calls in this path.

From `backend/`, inspect the plan first:

```bash
python scripts/train_incident_classifier.py \
  --s3-uri s3://YOUR-EXISTING-BUCKET/training/approved.jsonl \
  --aws-account-id 123456789012 \
  --aws-bucket YOUR-EXISTING-BUCKET \
  --aws-prefix training
```

The output says `DRY RUN`; it neither accesses AWS nor trains. After checking
the scope and current charges, add `--execute-aws-read` to download and train a
**shadow** model locally. Add `--activate` only after the existing approved-data
and held-out evaluation gates pass. The S3 input is never automatically promoted.
The script reports the SHA-256 of the downloaded bytes and records the source
URI, account, and digest in the model registry's training metadata. It rejects
non-Standard storage classes and over-limit objects before
`GetObject`. Changing objects between HEAD and GET are guarded by `IfMatch`.

Example minimum IAM permissions, narrowed to your actual resource; the
`sts:GetCallerIdentity` check does not normally require an IAM allow statement:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:GetObject"],
    "Resource": "arn:aws:s3:::YOUR-EXISTING-BUCKET/training/approved.jsonl"
  }]
}
```

If the object uses SSE-KMS, decryption also needs tightly scoped `kms:Decrypt`;
the simplest low-cost path is an already-authorized dataset without introducing
a new KMS key. The CLI never writes to S3. See [S3 HeadObject permissions](https://docs.aws.amazon.com/AmazonS3/latest/API/API_HeadObject.html)
and [GetObject permissions](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObject.html).

## Investigation and response boundary

An AWS finding already imported as an incident can inform the AI investigation.
The model's recommendation remains a proposal, not a cloud change. Confirm the
affected account, resource, intended exposure, and evidence before using the
existing two-person response-action approval flow. With only $20 reported in
credits, keep AWS response disabled unless explicitly needed and verified.
