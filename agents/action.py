from pyairtable import Api
from datetime import datetime
from config import AIRTABLE_API_KEY, AIRTABLE_BASE_ID
import discord
from bot_instance import bot

api = Api(AIRTABLE_API_KEY)
action_queue = api.table(AIRTABLE_BASE_ID, "ActionQueue")


async def handle_action(decision: dict):
    tier = decision.get("tier", 1)
    founder_name = decision["founder_name"]
    startup_name = decision.get("startup_name", "Unknown")
    bot_message = decision.get("bot_message")

    if tier == 1:
        # Stay silent — just log it
        print(f"🔇 Tier 1 — no response for {founder_name}")
        return

    if tier == 2:
        # Send advice immediately, no operator involvement
        print(f"💬 Tier 2 — sending immediate advice to {founder_name}")
        await send_discord_message(founder_name, bot_message)
        return

    if tier == 3:
        # Queue for operator approval — don't send yet
        print(f"🚨 Tier 3 — queuing operator action for {founder_name}")
        operator_tasks = decision.get("operator_tasks", [])

        action_queue.create({
            "founder_name": founder_name,
            "startup_name": startup_name,
            "action_type": "escalate",
            "draft_message": bot_message or "",
            "reasoning": decision.get("reasoning", ""),
            "resource_suggestion": decision.get("resource_suggestion", ""),
            "operator_tasks": "\n".join(
                [f"• {t}" for t in operator_tasks]
            ),
            "status": "PENDING",
            "created_at": datetime.now().isoformat()
        })

        # Ping ops-team so operators know to check the dashboard
        await ping_ops_team(founder_name, startup_name, decision.get("reasoning", ""))

async def ping_ops_team(founder_name: str, startup_name: str, reasoning: str):
    """Notify #ops-team that a new action needs their review on the dashboard."""
    for guild in bot.guilds:
        ops_channel = discord.utils.get(guild.channels, name="ops-team")
        if ops_channel:
            await ops_channel.send(
                f"📬 **New action added to the dashboard queue**\n"
                f"**Founder:** {founder_name} — **{startup_name}**\n"
                f"**Reason:** {reasoning}\n"
                f"👉 Review and approve on the DecisionStack dashboard."
            )
            print(f"✅ Ops team pinged for {founder_name}")
            return
    print("❌ ops-team channel not found")

async def send_discord_message(founder_name: str, message: str):
    """Send a message to #founder-updates."""
    for guild in bot.guilds:
        channel = discord.utils.get(guild.channels, name="founder-updates")
        if channel:
            await channel.send(f"Hey {founder_name} — {message}")
            print(f"✅ Message sent to {founder_name}")
            return
    print("❌ founder-updates channel not found")