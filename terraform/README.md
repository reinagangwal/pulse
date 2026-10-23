# Pulse — Terraform

Codifies every AWS resource Pulse runs on: the 3 Lambda functions, the
`bot-checkins` DynamoDB table, the 4 EventBridge Scheduler schedules, the
Secrets Manager secret containers, the IAM policies granting Lambda read
access to those secrets, the CloudWatch error alarms + dashboard, the SNS
alert topic, and the monthly AWS Budget alert.

## Important — these resources already exist

Every resource in this directory was created by hand (console/CLI) before
this Terraform was written. **Do not run `terraform apply` directly** — it
will try to create duplicates of resources that are already live, and at
best fail, at worst conflict with the running system.

Before `apply` is safe, each resource must be adopted into Terraform state
with `terraform import` (see the NOTE comment at the top of each `.tf`
file for the exact import command for every resource it defines).

## What's verified vs. not

- `terraform init` / `validate` / `plan` — written and internally
  consistent, not yet run against the live AWS account.
- `terraform import` for each resource, followed by a clean `plan` with
  zero diff — the step that proves this IaC actually matches reality.
  Not done yet; do this with time to spare, not minutes before a demo.
- `apply` — only ever meaningful after every resource above is imported.

## Usage once imported

```
terraform init
terraform plan -var="account_id=<aws-account-id>" -var="alert_email=<your-email>" -var="my_whatsapp_number=whatsapp:+91XXXXXXXXXX"
```
