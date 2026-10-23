# The three daily check-in schedules and the close-out schedule.
# NOTE: if these already exist by hand, import before applying, e.g.:
#   terraform import aws_scheduler_schedule.morning_checkin pulse-morning-checkin

resource "aws_scheduler_schedule" "morning_checkin" {
  name                = "pulse-morning-checkin"
  schedule_expression = "cron(0 7 * * ? *)"
  schedule_expression_timezone = "Asia/Calcutta"
  flexible_time_window { mode = "OFF" }

  target {
    arn      = aws_lambda_function.bot_send_checkin.arn
    role_arn = "arn:aws:iam::${var.account_id}:role/service-role/bot-send-checkin-role-q2rzbatu"
    input    = jsonencode({ checkin_type = "morning" })
  }
}

resource "aws_scheduler_schedule" "midday_checkin" {
  name                          = "pulse-midday-checkin"
  schedule_expression           = "cron(0 13 * * ? *)"
  schedule_expression_timezone  = "Asia/Calcutta"
  flexible_time_window { mode = "OFF" }

  target {
    arn      = aws_lambda_function.bot_send_checkin.arn
    role_arn = "arn:aws:iam::${var.account_id}:role/service-role/bot-send-checkin-role-q2rzbatu"
    input    = jsonencode({ checkin_type = "midday" })
  }
}

resource "aws_scheduler_schedule" "evening_checkin" {
  name                          = "pulse-evening-checkin"
  schedule_expression           = "cron(0 21 * * ? *)"
  schedule_expression_timezone  = "Asia/Calcutta"
  flexible_time_window { mode = "OFF" }

  target {
    arn      = aws_lambda_function.bot_send_checkin.arn
    role_arn = "arn:aws:iam::${var.account_id}:role/service-role/bot-send-checkin-role-q2rzbatu"
    input    = jsonencode({ checkin_type = "evening" })
  }
}

resource "aws_scheduler_schedule" "close_out_day" {
  name                          = "pulse-close-out-day"
  schedule_expression           = "cron(30 23 * * ? *)"
  schedule_expression_timezone  = "Asia/Calcutta"
  flexible_time_window { mode = "OFF" }

  target {
    arn      = aws_lambda_function.bot_close_out_day.arn
    role_arn = "arn:aws:iam::${var.account_id}:role/service-role/bot-close-out-day-role-vh52sjdu"
  }
}
