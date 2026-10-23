resource "aws_dynamodb_table" "bot_checkins" {
  name         = "bot-checkins"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"
  range_key    = "checkin_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "checkin_id"
    type = "S"
  }
}
