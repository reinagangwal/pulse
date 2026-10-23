import os
import json
import boto3
import urllib.request
import urllib.error

_secrets_client = boto3.client('secretsmanager')
_secrets_cache = {}


def _get_secret(secret_id):
    if secret_id not in _secrets_cache:
        response = _secrets_client.get_secret_value(SecretId=secret_id)
        _secrets_cache[secret_id] = json.loads(response['SecretString'])
    return _secrets_cache[secret_id]


GROQ_API_KEY = _get_secret(os.environ.get('GROQ_SECRET_ID', 'pulse/groq'))['token']

# Groq's free tier — OpenAI-compatible chat completions API, fast inference.
# Swap this to the Bedrock model ID once AWS support grants access,
# and replace the _call_llm function with the Bedrock invoke_model call.
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_ID = "openai/gpt-oss-20b"

# All user-specific context is externalized to env vars below so the code
# itself carries no personal information — only generic fallback defaults.
USER_NAME = os.environ.get('USER_NAME', 'there')
USER_HABITS = os.environ.get(
    'USER_HABITS',
    '20-min movement, 2.5L water, a phone curfew, a short journal entry, one new concept learned'
)
WORK_DAY_LABEL = os.environ.get('WORK_DAY_LABEL', 'a work-from-office day')
HOME_DAY_LABEL = os.environ.get('HOME_DAY_LABEL', 'a work-from-home day')
WORK_DAY_SCHEDULE = os.environ.get(
    'WORK_DAY_SCHEDULE',
    "7:00am - Wake up, no phone, hydrate\n"
    "7:30am - Focused personal project time\n"
    "9:00am - Get ready and commute\n"
    "9:30am - Office / work block\n"
    "1:00pm - Lunch\n"
    "5:30pm - Clock out, commute home\n"
    "6:30pm - Movement / exercise\n"
    "7:30pm - Personal project or learning block\n"
    "9:30pm - Journal + plan tomorrow\n"
    "10:30pm - Phone down, sleep"
)
HOME_DAY_SCHEDULE = os.environ.get(
    'HOME_DAY_SCHEDULE',
    "7:00am - Wake up, no phone, hydrate\n"
    "7:15am - Movement / exercise\n"
    "9:30am - Deep work block (personal project or study)\n"
    "1:00pm - Lunch\n"
    "2:00pm - Remote work or project continuation\n"
    "5:00pm - Personal / family time\n"
    "9:30pm - Journal + plan tomorrow\n"
    "10:30pm - Phone down, sleep"
)

PERSONAL_CONTEXT = f"""You are a no-nonsense accountability partner for {USER_NAME}.

About {USER_NAME}:
- Motivated by consistency, but like most people sometimes struggles with comfort and procrastination
- Non-negotiable daily habits: {USER_HABITS}
- Alternates between {WORK_DAY_LABEL} and {HOME_DAY_LABEL} routines
- Building this WhatsApp accountability bot as a personal project

Your tone:
- Warm, encouraging, like a supportive friend who also holds you accountable
- Use emojis naturally — not excessively, but they should feel present
- Short — WhatsApp messages, not essays. 2-4 sentences maximum.
- Reference actual habits and streak when you have them
- When slipping: firm but kind. Remind them of the recovery protocol — never zero, never miss twice. Still use emojis.
- When on a streak: celebrate it genuinely, not briefly"""


def _call_llm(prompt):
    """
    Calls Groq's OpenAI-compatible chat completions endpoint using urllib
    (no extra dependencies). Returns the generated text string.
    """
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; pulse-bot/1.0)",
    }

    payload = json.dumps({
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": PERSONAL_CONTEXT},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 500,
        "temperature": 0.7,
    }).encode("utf-8")

    req = urllib.request.Request(GROQ_API_URL, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"Groq API error {e.code}: {error_body}")


def calculate_streak(streak_data):
    if not streak_data:
        return {'current_streak': 0, 'consecutive_misses': 0, 'total_replied': 0, 'total_missed': 0, 'warning': False}
    by_date = {}
    for checkin_id, record in streak_data.items():
        date_str = checkin_id.split('#')[0]
        if date_str not in by_date:
            by_date[date_str] = []
        by_date[date_str].append(record)
    sorted_dates = sorted(by_date.keys(), reverse=True)
    total_replied = sum(1 for r in streak_data.values() if r.get('status') == 'replied')
    total_missed = sum(1 for r in streak_data.values() if r.get('status') == 'missed')
    current_streak = 0
    for date in sorted_dates:
        if any(r.get('status') == 'replied' for r in by_date[date]):
            current_streak += 1
        else:
            break
    consecutive_misses = 0
    for date in sorted_dates:
        if all(r.get('status') == 'missed' for r in by_date[date]):
            consecutive_misses += 1
        else:
            break
    return {'current_streak': current_streak, 'consecutive_misses': consecutive_misses, 'total_replied': total_replied, 'total_missed': total_missed, 'warning': consecutive_misses >= 1}


def get_streak_context(streak_data):
    if not streak_data:
        return "No check-in history yet — this is one of the first days."
    s = calculate_streak(streak_data)
    parts = [f"Current streak: {s['current_streak']} day(s) with at least one reply."]
    if s['consecutive_misses'] >= 2:
        parts.append("WARNING: They have missed ALL check-ins for 2 or more days in a row. This breaks the recovery protocol. Be firm.")
    elif s['consecutive_misses'] == 1:
        parts.append("Caution: Yesterday was a full miss. One more full miss in a row breaks the recovery protocol — remind them.")
    parts.append(f"Overall: {s['total_replied']} replied, {s['total_missed']} missed in recent history.")
    return ' '.join(parts)


def generate_checkin_message(checkin_type, streak_data=None, is_work_day=None):
    streak_context = get_streak_context(streak_data or {})

    if is_work_day is True:
        day_context = f"Today is {WORK_DAY_LABEL}. Full schedule:\n{WORK_DAY_SCHEDULE}"
    elif is_work_day is False:
        day_context = f"Today is {HOME_DAY_LABEL}. Full schedule:\n{HOME_DAY_SCHEDULE}"
    else:
        day_context = "Day type unknown."

    prompts = {
        'morning': f"""Generate a warm, emoji-filled morning message for {USER_NAME}.
{day_context}
{streak_context}
Structure it as:
1. A warm good morning with their name
2. What today looks like (key blocks only)
3. One AI concept, buzzword, or trending topic worth exploring today — pick something genuinely interesting from the world of AI/ML right now, explain it in one sentence
4. A short motivating closer
No reply needed — this is their daily briefing. Keep it punchy and real.""",

        "midday": f"""Generate a midday check-in message for {USER_NAME}.
{day_context}
{streak_context}
Ask them one specific question: did they complete their morning movement or focus block?
They should reply yes or no. Under 2 sentences.""",

        "evening": f"""Generate an evening check-in message for {USER_NAME}.
{day_context}
{streak_context}
Ask if their journal is done and their phone is going down for the night.
They should reply yes or no. Under 2 sentences.""",
    }

    prompt = prompts.get(checkin_type)
    if not prompt:
        raise ValueError(f"Unknown checkin_type: {checkin_type}")

    return _call_llm(prompt)


def generate_acknowledgment(checkin_type, reply_text, streak_data=None):
    streak_context = get_streak_context(streak_data or {})

    prompt = f"""{USER_NAME} just replied to their {checkin_type} check-in with: "{reply_text}"
{streak_context}
Generate a brief acknowledgment (1-2 sentences max).
If yes/done/completed: brief positive acknowledgment, move on.
If no/missed: firm but not harsh — one miss is neutral but two in a row is not allowed.
If ambiguous: interpret charitably and acknowledge."""

    return _call_llm(prompt)
