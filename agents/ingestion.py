import anthropic
import json
from config import ANTHROPIC_API_KEY

claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


async def ingest_message(founder_name: str, message_content: str) -> dict:
    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system="""You are an AI that extracts structured data from 
        founder updates. Always return valid JSON only. 
        No explanation, no markdown, no code fences, just the raw JSON object.""",
        messages=[{
            "role": "user",
            "content": f"""
            Extract structured info from this founder update message.

            Return ONLY this JSON structure, no markdown, no backticks:
            {{
                "stage": "idea" | "mvp" | "growth" | "scaling",
                "blockers": ["blocker1", "blocker2"],
                "wins": ["win1", "win2"],
                "resolved_blockers": ["exact blocker text that has been resolved"],
                "sentiment": "positive" | "neutral" | "struggling",
                "needs_resource": true | false,
                "resource_type": "legal" | "funding" | "talent" | 
                                 "technical" | "marketing" | null
            }}

            Rules for resolved_blockers:
            - If the message indicates a previous problem is now fixed or no longer
              an issue, add it to resolved_blockers with a short description
              matching what the blocker would have been called.
            - Examples: "we found our frontend engineer" → resolved_blockers: ["frontend engineer"]
            - "we closed our funding round" → resolved_blockers: ["funding", "runway"]
            - "team is back together" → resolved_blockers: ["team members", "hiring"]
            - If nothing is resolved, return resolved_blockers: []

            Founder: {founder_name}
            Message: {message_content}
            """
        }]
    )

    raw = response.content[0].text.strip()
    print(f"Raw ingestion response: {raw}")

    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]).strip()

    if not raw:
        print("⚠️ Empty response from Claude, using fallback")
        return {
            "stage": "mvp",
            "blockers": [],
            "wins": [],
            "resolved_blockers": [],
            "sentiment": "neutral",
            "needs_resource": False,
            "resource_type": None
        }

    return json.loads(raw)