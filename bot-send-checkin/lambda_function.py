import os
import json
import boto3
from datetime import datetime, timezone, timedelta
from twilio.rest import Client
from bedrock_agent import generate_checkin_message

TWILIO_ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
TWILIO_AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']
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
