from pyairtable import Api
from datetime import datetime
from config import AIRTABLE_API_KEY, AIRTABLE_BASE_ID
import json

api = Api(AIRTABLE_API_KEY)
table = api.table(AIRTABLE_BASE_ID, "Startups")


def get_profile(founder_name: str) -> dict | None:
    """Fetch a startup's full profile from Airtable."""
    records = table.all(formula=f"{{founder_name}}='{founder_name}'")
    if records:
        return records[0]
    return None

def _resolve_and_deduplicate_blockers(
    existing_blockers: list,
    new_blockers: list,
    resolved_signals: list
) -> list:
    """
    Use Claude to intelligently merge, deduplicate, and resolve blockers.
    This handles fuzzy matches that simple string comparison misses.
    """
    if not existing_blockers and not new_blockers:
        return []

    import anthropic
    from config import ANTHROPIC_API_KEY
    claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system="You are a data cleaning assistant. Return only valid JSON arrays. No markdown, no explanation.",
        messages=[{
            "role": "user",
            "content": f"""
            Given these existing blockers, new blockers, and resolved signals,
            return a clean final list of blockers.

            Rules:
            1. Remove any blocker that is semantically resolved by the resolved_signals
               (e.g. "hiring" resolves "difficulty finding engineers", "team members",
               "engineer attrition", etc.)
            2. Merge duplicates — if two blockers mean the same thing, keep only
               the clearest/shortest version
            3. Add new_blockers only if they are not already covered
            4. Return only genuinely current, unresolved blockers
            5. If everything is resolved or there are no real blockers, return []

            Existing blockers: {existing_blockers}
            New blockers from latest message: {new_blockers}
            Resolved signals (things that are now fixed): {resolved_signals}

            Return ONLY a JSON array of strings, e.g. ["blocker1", "blocker2"]
            """
        }]
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]).strip()

    try:
        result = json.loads(raw)
        print(f"🧹 Cleaned blockers: {result}")
        return result if isinstance(result, list) else []
    except Exception as e:
        print(f"⚠️ Blocker cleanup failed: {e}, keeping existing")
        return existing_blockers

def upsert_profile(founder_name: str, ingested_data: dict):
    """
    Create or update a startup profile.
    Only overwrites fields if the new message contains meaningful data.
    Blockers are resolved and deduplicated using Claude.
    """
    existing = get_profile(founder_name)
    now = datetime.now().isoformat()

    if existing:
        record_id = existing["id"]
        old_fields = existing["fields"]
        old_count = old_fields.get("interaction_count", 0)

        # --- Blockers: Claude-powered resolve + deduplicate ---
        existing_blockers_str = old_fields.get("blockers", "")
        existing_blockers = (
            [b.strip() for b in existing_blockers_str.split(",") if b.strip()]
            if existing_blockers_str else []
        )
        new_blockers = ingested_data.get("blockers", [])
        resolved = ingested_data.get("resolved_blockers", [])

        merged_blockers = _resolve_and_deduplicate_blockers(
            existing_blockers, new_blockers, resolved
        )

        # --- Wins: merge, no duplicates ---
        existing_wins_str = old_fields.get("wins", "")
        existing_wins = (
            [w.strip() for w in existing_wins_str.split(",") if w.strip()]
            if existing_wins_str else []
        )
        new_wins = ingested_data.get("wins", [])
        merged_wins = existing_wins.copy()
        for w in new_wins:
            if w.lower() not in [x.lower() for x in existing_wins]:
                merged_wins.append(w)

        # --- Stage: only update if new message has a real stage signal ---
        new_stage = ingested_data.get("stage", "")
        old_stage = old_fields.get("stage", "")
        stage = new_stage if new_stage else old_stage

        # --- Sentiment: only update if new blockers or wins exist ---
        has_meaningful_content = bool(new_blockers) or bool(new_wins)
        sentiment = (
            ingested_data.get("sentiment", old_fields.get("sentiment", "neutral"))
            if has_meaningful_content
            else old_fields.get("sentiment", "neutral")
        )

        fields = {
            "stage": stage,
            "blockers": ", ".join(merged_blockers),
            "wins": ", ".join(merged_wins),
            "sentiment": sentiment,
            "last_seen": now,
            "interaction_count": old_count + 1,
        }

        if "startup_name" in ingested_data:
            fields["startup_name"] = ingested_data["startup_name"]

        table.update(record_id, fields)
        return {**old_fields, **fields}

    else:
        # Brand new founder — create fresh record
        fields = {
            "founder_name": founder_name,
            "startup_name": ingested_data.get("startup_name", ""),
            "stage": ingested_data.get("stage", "idea"),
            "blockers": ", ".join(ingested_data.get("blockers", [])),
            "wins": ", ".join(ingested_data.get("wins", [])),
            "sentiment": ingested_data.get("sentiment", "neutral"),
            "last_seen": ingested_data.get("registered_at", datetime.now().isoformat()),
            "interaction_count": 0,
            "health_status": "healthy",
        }
        new_record = table.create(fields)
        return new_record["fields"]


def get_all_profiles() -> list:
    """Get every startup profile — used by the proactive agent."""
    return table.all()


def update_health_status(founder_name: str, status: str):
    """Update just the health status field."""
    existing = get_profile(founder_name)
    if existing:
        table.update(existing["id"], {"health_status": status})


wellness_table = api.table(AIRTABLE_BASE_ID, "WellnessAlerts")

def log_wellness_alert(founder_name: str, startup_name: str):
    """Log a wellness alert — dashboard reads from this table."""
    wellness_table.create({
        "founder_name": founder_name,
        "startup_name": startup_name,
        "triggered_at": datetime.now().isoformat(),
        "status": "ACTIVE"
    })
    print(f"🚨 Wellness alert logged for {founder_name}")