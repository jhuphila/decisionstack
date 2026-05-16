import anthropic
import json
from config import ANTHROPIC_API_KEY

claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

MENTAL_HEALTH_RESOURCES = """
**You're not alone — here are some resources available to you right now:**
- **988 Suicide & Crisis Lifeline** — Call or text **988** (US, 24/7)
- **Crisis Text Line** — Text **HOME** to **741741** (24/7)
- **NAMI Helpline** — 1-800-950-6264 (Mon–Fri, 10am–10pm ET)
- **International resources** — findahelpline.com

These are confidential and free. Please reach out to them.
"""

async def check_for_crisis(message_content: str) -> bool:
    """
    Returns True if the message contains a mental health crisis signal.
    Intentionally sensitive — better to flag too much than miss something.
    """
    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=10,
        system="""You are a content safety classifier. 
        Return only the word YES or NO. Nothing else.""",
        messages=[{
            "role": "user",
            "content": f"""Does this message contain any signal of:
            - suicidal ideation or self-harm
            - severe mental distress or breakdown
            - statements suggesting the person may hurt themselves
            - expressions of hopelessness about life (not just their startup)

            Be sensitive — flag anything that could indicate a person
            is struggling beyond normal startup stress.

            Message: {message_content}

            Reply YES or NO only."""
        }]
    )

    result = response.content[0].text.strip().upper()
    print(f"🔍 Crisis check result: {result}")
    return result == "YES"


def get_crisis_founder_message(founder_name: str) -> str:
    return (
        f"Hey {founder_name}, we noticed your message and want to make sure "
        f"you have access to support beyond what we can offer here.\n\n"
        f"{MENTAL_HEALTH_RESOURCES}\n"
        f"The Foundry team has been notified and will follow up with you."
    )