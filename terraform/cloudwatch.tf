# NOTE: already created by hand tonight — import before applying:
#   terraform import aws_sns_topic.alerts pulse-alerts
#   terraform import aws_cloudwatch_metric_alarm.send_checkin_errors pulse-bot-send-checkin-errors
#   terraform import aws_cloudwatch_metric_alarm.webhook_handler_errors pulse-bot-webhook-handler-errors
#   terraform import aws_cloudwatch_metric_alarm.close_out_day_errors pulse-bot-close-out-day-errors
#   terraform import aws_cloudwatch_dashboard.pulse Pulse

resource "aws_sns_topic" "alerts" {
  name = "pulse-alerts"
}

resource "aws_sns_topic_subscription" "alerts_email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

locals {
  functions = {
    send_checkin     = aws_lambda_function.bot_send_checkin.function_name
    webhook_handler  = aws_lambda_function.bot_webhook_handler.function_name
    close_out_day    = aws_lambda_function.bot_close_out_day.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "errors" {
  for_each            = local.functions
  alarm_name          = "pulse-${each.value}-errors"
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = each.value }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_dashboard" "pulse" {
  dashboard_name = "Pulse"
  dashboard_body = file("${path.module}/../dashboard.json")
}
