import os
import json
import urllib.request
import urllib.error

HF_API_TOKEN = os.environ['HF_API_TOKEN']

# Mistral 7B Instruct — best free option on HuggingFace for instruction following.
# Swap this to the Bedrock model ID once AWS support grants access,
# and replace the _call_hf function with the Bedrock invoke_model call.
HF_API_URL = "https://router.huggingface.co/v1/chat/completions"
MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct:fastest"

# All user-specific context is externalized to env vars below so the code
# itself carries no personal information — only generic fallback defaults.
USER_NAME = os.environ.get('USER_NAME', 'there')
USER_HABITS = os.environ.get(
    'USER_HABITS',
    '20-min movement, 2.5L water, a phone curfew, a short journal entry, one new concept learned'
)
WORK_DAY_LABEL = os.environ.get('WORK_DAY_LABEL', 'a work-from-office day')
HOME_DAY_LABEL = os.environ.get('HOME_DAY_LABEL', 'a work-from-home day')

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


def _call_hf(prompt):
    """
    Calls HuggingFace Inference API using urllib (no extra dependencies).
    Returns the generated text string.
    """
    headers = {
        "Authorization": f"Bearer {HF_API_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = json.dumps({
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": PERSONAL_CONTEXT},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 150,
        "temperature": 0.7,
    }).encode("utf-8")

    req = urllib.request.Request(HF_API_URL, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"HuggingFace API error {e.code}: {error_body}")


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
        day_context = f"Today is {WORK_DAY_LABEL}."
    elif is_work_day is False:
        day_context = f"Today is {HOME_DAY_LABEL}."
    else:
        day_context = "Day type unknown."

    prompts = {
        'morning': f"""Generate a warm, detailed morning briefing for {USER_NAME}.
{day_context}
{streak_context}
Structure it exactly like this:
1. Warm good morning with their name and a motivating opener (1 sentence)
2. A to-the-minute schedule for today — every block from wake-up to sleep, with exact times. Use the day context provided. Format each item on its own line with a relevant emoji and the time.
3. One AI concept or trending topic worth exploring today — pick something genuinely interesting, explain it in one sentence
4. A short warm closer (1 sentence)
Keep it punchy. This is their daily briefing, not a chat message — they read it like an agenda.""",

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

    return _call_hf(prompt)


def generate_acknowledgment(checkin_type, reply_text, streak_data=None):
    streak_context = get_streak_context(streak_data or {})

    prompt = f"""{USER_NAME} just replied to their {checkin_type} check-in with: "{reply_text}"
{streak_context}
Generate a brief acknowledgment (1-2 sentences max).
If yes/done/completed: brief positive acknowledgment, move on.
If no/missed: firm but not harsh — one miss is neutral but two in a row is not allowed.
If ambiguous: interpret charitably and acknowledge."""

    return _call_hf(prompt)
