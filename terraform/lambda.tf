# NOTE: these functions already exist and were created by hand. Before
# `terraform apply` is ever safe against the live account, each one must
# first be adopted into state with `terraform import`, e.g.:
#   terraform import aws_lambda_function.bot_send_checkin bot-send-checkin
#   terraform import aws_lambda_function.bot_webhook_handler bot-webhook-handler
#   terraform import aws_lambda_function.bot_close_out_day bot-close-out-day
# Running `apply` without importing first would try to CREATE duplicates
# and fail (or, worse, conflict with the live functions) — see README.md.

data "archive_file" "bot_send_checkin" {
  type        = "zip"
  source_dir  = "${path.module}/../bot-send-checkin"
  output_path = "${path.module}/.build/bot-send-checkin.zip"
}

resource "aws_lambda_function" "bot_send_checkin" {
  function_name    = "bot-send-checkin"
  role              = "arn:aws:iam::${var.account_id}:role/service-role/bot-send-checkin-role-q2rzbatu"
  handler           = "lambda_function.lambda_handler"
  runtime           = "python3.14"
  timeout           = 60
  memory_size       = 128
  filename          = data.archive_file.bot_send_checkin.output_path
  source_code_hash  = data.archive_file.bot_send_checkin.output_base64sha256

  environment {
    variables = {
      TABLE_NAME            = aws_dynamodb_table.bot_checkins.name
      USER_ID                = "demo_user"
      TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"
      MY_WHATSAPP_NUMBER     = var.my_whatsapp_number
      USER_NAME               = var.user_name
      USER_HABITS             = var.user_habits
      WORK_DAY_LABEL          = var.work_day_label
      HOME_DAY_LABEL          = var.home_day_label
      WORK_DAYS               = var.work_days
      WORK_DAY_SCHEDULE       = var.work_day_schedule
      HOME_DAY_SCHEDULE       = var.home_day_schedule
    }
  }
}

data "archive_file" "bot_webhook_handler" {
  type        = "zip"
  source_dir  = "${path.module}/../bot-webhook-handler"
  output_path = "${path.module}/.build/bot-webhook-handler.zip"
}

resource "aws_lambda_function" "bot_webhook_handler" {
  function_name    = "bot-webhook-handler"
  role              = "arn:aws:iam::${var.account_id}:role/bot-webhook-handler-role-qgy0srze"
  handler           = "lambda_function.lambda_handler"
  runtime           = "python3.14"
  timeout           = 60
  memory_size       = 128
  filename          = data.archive_file.bot_webhook_handler.output_path
  source_code_hash  = data.archive_file.bot_webhook_handler.output_base64sha256

  environment {
    variables = {
      TABLE_NAME     = aws_dynamodb_table.bot_checkins.name
      USER_ID         = "demo_user"
      USER_NAME       = var.user_name
      USER_HABITS     = var.user_habits
      WORK_DAY_LABEL  = var.work_day_label
      HOME_DAY_LABEL  = var.home_day_label
    }
  }

  function_url_config {
    authorization_type = "NONE"
  }
}

resource "aws_lambda_function_url" "bot_webhook_handler_url" {
  function_name      = aws_lambda_function.bot_webhook_handler.function_name
  authorization_type = "NONE"
}

data "archive_file" "bot_close_out_day" {
  type        = "zip"
  source_dir  = "${path.module}/../bot-close-out-day"
  output_path = "${path.module}/.build/bot-close-out-day.zip"
}

resource "aws_lambda_function" "bot_close_out_day" {
  function_name    = "bot-close-out-day"
  role              = "arn:aws:iam::${var.account_id}:role/service-role/bot-close-out-day-role-vh52sjdu"
  handler           = "lambda_function.lambda_handler"
  runtime           = "python3.14"
  timeout           = 30
  memory_size       = 128
  filename          = data.archive_file.bot_close_out_day.output_path
  source_code_hash  = data.archive_file.bot_close_out_day.output_base64sha256

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.bot_checkins.name
      USER_ID     = "demo_user"
    }
  }
}
