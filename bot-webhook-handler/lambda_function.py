import json
import os
import boto3
from datetime import datetime, timezone, timedelta
from urllib.parse import parse_qs
from bedrock_agent import generate_acknowledgment

IST_OFFSET = timedelta(hours=5, minutes=30)
IST = timezone(IST_OFFSET)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('TABLE_NAME', 'bot-checkins'))
USER_ID = os.environ.get('USER_ID', 'demo_user')


def determine_checkin_type():
    now_ist = datetime.now(IST)
    hour = now_ist.hour
    if hour < 11:
        return 'morning'
    elif hour < 17:
        return 'midday'
    else:
        return 'evening'


def get_recent_streak():
    try:
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(USER_ID),
            ScanIndexForward=False,
            Limit=21,
        )
        items = response.get('Items', [])
        return {item['checkin_id']: item for item in items}
    except Exception as e:
        print(f"Warning: could not fetch streak data: {e}")
        return {}


def lambda_handler(event, context):
    body = event.get('body', '')
    if event.get('isBase64Encoded'):
        import base64
        body = base64.b64decode(body).decode('utf-8')

    parsed = parse_qs(body)
    message_text = parsed.get('Body', [''])[0].strip()
    from_number = parsed.get('From', [''])[0]

    if not message_text:
        return _twiml_response('')

    checkin_type = determine_checkin_type()
    now_ist = datetime.now(IST)
    date_str = now_ist.strftime('%Y-%m-%d')
    checkin_id = f"{date_str}#{checkin_type}"

    # Write reply to DynamoDB
    table.put_item(
        Item={
            'user_id': USER_ID,
            'checkin_id': checkin_id,
            'checkin_type': checkin_type,
            'status': 'replied',
            'reply_text': message_text,
            'from_number': from_number,
            'timestamp': now_ist.isoformat(),
        }
    )

    # Fetch streak context then generate acknowledgment via Bedrock
    streak_data = get_recent_streak()
    ack_message = generate_acknowledgment(
        checkin_type=checkin_type,
        reply_text=message_text,
        streak_data=streak_data,
    )

    return _twiml_response(ack_message)


def _twiml_response(message_text):
    if message_text:
        body = f'<Response><Message>{_escape_xml(message_text)}</Message></Response>'
    else:
        body = '<Response></Response>'
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'text/xml'},
        'body': body,
    }


def _escape_xml(text):
    return (
        text.replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
    )
