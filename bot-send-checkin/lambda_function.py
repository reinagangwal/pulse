import os
import json
import boto3
from datetime import datetime, timezone, timedelta
from twilio.rest import Client
from bedrock_agent import generate_checkin_message

_secrets_client = boto3.client('secretsmanager')
_secrets_cache = {}


def _get_secret(secret_id):
    """Fetches and JSON-parses a secret, caching it for the life of this
    execution environment so we're not calling Secrets Manager on every
    single invocation — only on cold start."""
    if secret_id not in _secrets_cache:
        response = _secrets_client.get_secret_value(SecretId=secret_id)
        _secrets_cache[secret_id] = json.loads(response['SecretString'])
    return _secrets_cache[secret_id]


_twilio_secret = _get_secret(os.environ.get('TWILIO_SECRET_ID', 'pulse/twilio'))
TWILIO_ACCOUNT_SID = _twilio_secret['account_sid']
TWILIO_AUTH_TOKEN = _twilio_secret['auth_token']
TWILIO_WHATSAPP_NUMBER = os.environ['TWILIO_WHATSAPP_NUMBER']
MY_WHATSAPP_NUMBER = os.environ['MY_WHATSAPP_NUMBER']
TABLE_NAME = os.environ.get('TABLE_NAME', 'bot-checkins')
USER_ID = os.environ.get('USER_ID', 'demo_user')
WORK_DAYS = {int(d) for d in os.environ.get('WORK_DAYS', '1,2,3').split(',') if d.strip()}

IST = timezone(timedelta(hours=5, minutes=30))

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)


def is_work_day():
    """
    Returns True if today is a work-from-office day, False if it's a
    work-from-home day. Configure via the WORK_DAYS env var — a
    comma-separated list of weekday numbers (0=Monday ... 6=Sunday).
    Defaults to Tuesday-Thursday in office, rest from home.
    """
    now_ist = datetime.now(IST)
    return now_ist.weekday() in WORK_DAYS


def get_recent_streak(days=7):
    """
    Fetches the last 7 days of check-in records from DynamoDB
    to give Bedrock streak context.
    """
    try:
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(USER_ID),
            ScanIndexForward=False,
            Limit=21,  # up to 3 check-ins per day × 7 days
        )
        items = response.get('Items', [])
        # Build a simple dict keyed by checkin_id for easy reading
        return {item['checkin_id']: item for item in items}
    except Exception as e:
        # Streak context is non-critical — don't let a DynamoDB failure
        # stop the message from being sent
        print(f"Warning: could not fetch streak data: {e}")
        return {}


def lambda_handler(event, context):
    checkin_type = event.get('checkin_type')

    if not checkin_type:
        raise ValueError("event must include 'checkin_type' (morning/midday/evening)")

    streak_data = get_recent_streak()
    work_day = is_work_day()

    # Generate message via Bedrock
    message_body = generate_checkin_message(
        checkin_type=checkin_type,
        streak_data=streak_data,
        is_work_day=work_day,
    )

    # Belt-and-suspenders: never let an empty/odd model response block the
    # actual check-in from going out.
    if not message_body or not message_body.strip():
        print(f"Warning: model returned empty content for {checkin_type}; using fallback message")
        message_body = f"⏰ Time for your {checkin_type} check-in!"

    # Send via Twilio
    message = client.messages.create(
        from_=TWILIO_WHATSAPP_NUMBER,
        to=MY_WHATSAPP_NUMBER,
        body=message_body,
    )

    return {
        'statusCode': 200,
        'checkin_type': checkin_type,
        'message_sid': message.sid,
        'message_body': message_body,
    }
