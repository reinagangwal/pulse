variable "aws_region" {
  description = "AWS region Pulse is deployed in"
  type        = string
  default     = "us-east-1"
}

variable "account_id" {
  description = "AWS account ID Pulse is deployed in"
  type        = string
}

variable "my_whatsapp_number" {
  description = "WhatsApp number check-ins are sent to, e.g. whatsapp:+1XXXXXXXXXX"
  type        = string
  sensitive   = true
}

variable "user_name" {
  type    = string
  default = "there"
}

variable "user_habits" {
  type    = string
  default = "20-min movement, 2.5L water, a phone curfew, a short journal entry, one new concept learned"
}

variable "work_day_label" {
  type    = string
  default = "a work-from-office day"
}

variable "home_day_label" {
  type    = string
  default = "a work-from-home day"
}

variable "work_days" {
  description = "Comma-separated weekday numbers (0=Monday ... 6=Sunday) treated as office days"
  type        = string
  default     = "1,2,3"
}

variable "work_day_schedule" {
  type    = string
  default = ""
}

variable "home_day_schedule" {
  type    = string
  default = ""
}

variable "alert_email" {
  description = "Email address for CloudWatch alarm and budget notifications"
  type        = string
}

variable "monthly_budget_usd" {
  type    = string
  default = "15"
}
