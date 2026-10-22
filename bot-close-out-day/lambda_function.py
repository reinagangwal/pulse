import os
import json
import boto3
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
TABLE_NAME = os.environ.get('TABLE_NAME', 'bot-checkins')
USER_ID = os.environ.get('USER_ID', 'demo_user')
CHECKIN_TYPES = ['morning', 'midday', 'evening']

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)


def get_todays_checkins(date_str):
    """
    Fetches all check-in records for today from DynamoDB.
    Returns a set of checkin_types that already have a record.
    """
    response = table.query(
        KeyConditionExpression=(
            boto3.dynamodb.conditions.Key('user_id').eq(USER_ID) &
            boto3.dynamodb.conditions.Key('checkin_id').begins_with(date_str)
        )
    )
    return {item['checkin_type'] for item in response.get('Items', [])}


def write_missed(date_str, checkin_type, now_ist):
    """
    Writes a 'missed' record for a check-in type that had no reply today.
    Uses a different key suffix to avoid overwriting a real reply that
    might arrive in the last few seconds before close-out fires.
    """
    table.put_item(
        Item={
            'user_id': USER_ID,
            'checkin_id': f"{date_str}#{checkin_type}",
            'checkin_type': checkin_type,
            'status': 'missed',
            'reply_text': '',
            'timestamp': now_ist.isoformat(),
        },
        # Only write if no record exists yet — don't overwrite a real reply
        ConditionExpression='attribute_not_exists(checkin_id)',
    )


def lambda_handler(event, context):
    now_ist = datetime.now(IST)
    date_str = now_ist.strftime('%Y-%m-%d')

    # Find which check-ins already have a record today
    replied_types = get_todays_checkins(date_str)

    missed = []
    skipped = []

    for checkin_type in CHECKIN_TYPES:
        if checkin_type in replied_types:
            skipped.append(checkin_type)
            continue

        try:
            write_missed(date_str, checkin_type, now_ist)
            missed.append(checkin_type)
        except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            # A reply came in between the query and the write — that's fine,
            # the real reply is already there, nothing to do
            skipped.append(checkin_type)

    return {
        'statusCode': 200,
        'date': date_str,
        'missed_written': missed,
        'already_had_reply': skipped,
    }
