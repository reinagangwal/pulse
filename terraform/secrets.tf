# NOTE: already created by hand tonight — import before applying:
#   terraform import aws_secretsmanager_secret.twilio pulse/twilio
#   terraform import aws_secretsmanager_secret.groq pulse/groq
# Terraform manages the secret CONTAINERS here, not their values — actual
# secret values are set out-of-band (console/CLI) and never belong in
# version control or Terraform state in plaintext.

resource "aws_secretsmanager_secret" "twilio" {
  name = "pulse/twilio"
}

resource "aws_secretsmanager_secret" "groq" {
  name = "pulse/groq"
}

resource "aws_iam_role_policy" "send_checkin_secrets" {
  name = "pulse-secrets-read"
  role = "bot-send-checkin-role-q2rzbatu"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "secretsmanager:GetSecretValue"
      Resource = [
        "${aws_secretsmanager_secret.twilio.arn}*",
        "${aws_secretsmanager_secret.groq.arn}*",
      ]
    }]
  })
}

resource "aws_iam_role_policy" "webhook_handler_secrets" {
  name = "pulse-secrets-read"
  role = "bot-webhook-handler-role-qgy0srze"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "secretsmanager:GetSecretValue"
      Resource = "${aws_secretsmanager_secret.groq.arn}*"
    }]
  })
}
