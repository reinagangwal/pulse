# NOTE: already created by hand tonight — import before applying:
#   terraform import aws_budgets_budget.monthly pulse-monthly-budget

resource "aws_budgets_budget" "monthly" {
  name         = "pulse-monthly-budget"
  budget_type  = "COST"
  limit_amount = var.monthly_budget_usd
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator       = "GREATER_THAN"
    threshold                 = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }
}
