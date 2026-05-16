import anthropic
import json
from datetime import datetime, timezone
from config import ANTHROPIC_API_KEY

claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


async def reason(founder_name: str, profile: dict, latest_message: str = "") -> dict:
    """
    Given a full startup profile, decide what action to take.
    Returns a tier 1, 2, or 3 decision.
    """
    fields = profile.get("fields", profile)

    last_seen_str = fields.get("last_seen", "")
    days_silent = 0
    if last_seen_str:
        last_seen = datetime.fromisoformat(last_seen_str)
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
        days_silent = (datetime.now(timezone.utc) - last_seen).days

    if days_silent > 10:
        health = "silent"
    elif days_silent > 5:
        health = "at-risk"
    else:
        health = "healthy"

    current_sentiment = fields.get("sentiment", "neutral")
    if current_sentiment == "struggling" and health == "healthy":
        health = "at-risk"

    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system="""You are the AI operations manager for The Foundry,
        a startup community. You help route founder messages to the
        right level of response.
        Never ask founders follow-up questions or suggest calls.
        Never say things like 'are you open to a call' or 'let me know if you want to chat'.
        The bot is an automated communicator only — it cannot schedule meetings or take actions.
        Never use motivational language, metaphors, or AI-sounding encouragement.
        Write like a knowledgeable colleague giving quick practical advice, not a life coach.
        Avoid phrases like: 'you've got this', 'that takes resilience', 'keep pushing',
        'you're not alone in this', 'that's impressive', 'first and foremost',
        'it sounds like you', or any motivational filler.
        Always return valid JSON only. No markdown. No code fences. No backticks.""",
        messages=[{
            "role": "user",
            "content": f"""
            Analyze this founder profile and classify into exactly one tier.

            IMPORTANT — HOW TO USE THE DATA BELOW:
            "Latest message" is what the founder JUST said and is the most
            important signal. Use it as the primary input for your decision.
            "Historical blockers" are from previous messages and may be outdated
            — do NOT treat them as current problems if the latest message
            contradicts them or indicates things are going well.
            If the latest message is positive or neutral with no new blockers,
            default to Tier 1 unless there is a clear unresolved urgent issue
            explicitly mentioned in the latest message itself.

            Founder: {founder_name}
            Startup: {fields.get('startup_name', 'unknown')}
            Stage: {fields.get('stage', 'unknown')}
            Latest message: {latest_message if latest_message else 'N/A (proactive scan)'}
            Historical blockers (may be outdated): {fields.get('blockers', 'none')}
            Recent wins: {fields.get('wins', 'none')}
            Current sentiment: {fields.get('sentiment', 'neutral')}
            Days silent: {days_silent}
            Health: {health}

            TIER RULES:
            TIER 1 — No response needed
            Use when: latest message is casual, positive update, venting without
            asking for help, or celebrating. If the founder sounds like things
            are going well or improving, this is almost always Tier 1.
            Bot stays completely silent.

            TIER 2 — Immediate general advice
            Use when: latest message explicitly asks a general question or wants
            tips (e.g. "any advice on X", "how do I Y"). No operator needed.

            TIER 3 — Needs Foundry operator attention
            Use when: latest message explicitly describes a serious active blocker
            the Foundry needs to help with RIGHT NOW. Do not use historical
            blockers as the reason for Tier 3 if the latest message doesn't
            mention them. The trigger must come from the latest message itself.

            Return ONLY this JSON, no markdown, no backticks:
            {{
                "tier": 1,
                "reasoning": "one sentence explaining the tier choice",
                "bot_message": null,
                "operator_tasks": [],
                "resource_suggestion": null
            }}

            For tier 2, bot_message should be practical and direct — one or two
            concrete suggestions in plain language. No metaphors, no motivational
            language, no filler phrases.

            For tier 3, bot_message should follow this structure exactly:
            - One plain sentence acknowledging the specific situation from the
              latest message only
            - One concrete, actionable suggestion
            - End with exactly:
              "We've notified the Foundry operators and they'll be in touch about [specific thing]."
            Keep it under 4 sentences total. No motivational filler whatsoever.

            For tier 3, operator_tasks should be a list of 1-3 specific strings
            based only on what the latest message describes, not historical blockers.
            operator_tasks must be [] for tiers 1 and 2.
            """
        }]
    )

    raw = response.content[0].text.strip()
    print(f"Raw reasoning response: {raw}")

    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]).strip()

    if not raw:
        print("⚠️ Empty reasoning response, using fallback")
        return {
            "tier": 1,
            "reasoning": "Empty response from Claude — defaulting to no action",
            "bot_message": None,
            "operator_tasks": [],
            "resource_suggestion": None,
            "health_status": health,
            "founder_name": founder_name,
            "startup_name": fields.get("startup_name", "Unknown")
        }

    decision = json.loads(raw)
    decision["health_status"] = health
    decision["founder_name"] = founder_name
    decision["startup_name"] = fields.get("startup_name", "Unknown")
    return decision