import threading
import discord
import asyncio
from discord import app_commands
from datetime import datetime
from bot_instance import bot
from config import DISCORD_TOKEN, DISCORD_GUILD_ID
from scheduler import start_scheduler
from agents.ingestion import ingest_message
from memory.store import upsert_profile, get_profile, update_health_status
from agents.reasoning import reason
from agents.action import handle_action
from agents.crisis import check_for_crisis
import webhook

tree = app_commands.CommandTree(bot)
MY_GUILD = discord.Object(id=DISCORD_GUILD_ID)

# --- Message buffer ---
# Stores pending messages per founder before processing
# Structure: { "founder_name": { "messages": [], "timer": Timer, "startup_name": str } }
message_buffer = {}
BUFFER_WINDOW_SECONDS = 15  # wait 15 seconds for more messages before processing


async def process_buffer(founder_name: str):
    if founder_name not in message_buffer:
        return

    buffer_data = message_buffer.pop(founder_name)
    messages = buffer_data["messages"]
    startup_name = buffer_data["startup_name"]

    if not messages:
        return

    combined_content = " ".join(messages)
    print(f"📨 Combined {len(messages)} message(s) from "
          f"{founder_name} ({startup_name}): {combined_content}")

    # --- Crisis check FIRST before anything else ---
    is_crisis = await check_for_crisis(combined_content)
    if is_crisis:
        print(f"🚨 WELLNESS ALERT triggered for {founder_name}")
        await handle_crisis(founder_name, startup_name)
        return  # stop here — don't run normal pipeline

    ## Normal pipeline
    structured = await ingest_message(founder_name, combined_content)
    structured["startup_name"] = startup_name
    print(f"📊 Ingested: {structured}")

    upsert_profile(founder_name, structured)

    full_profile = get_profile(founder_name)
    # Pass the latest message so reasoning can weigh it against stale blockers
    decision = await reason(founder_name, full_profile, latest_message=combined_content)
    print(f"🧠 Decision: {decision}")

    update_health_status(founder_name, decision["health_status"])
    await handle_action(decision)

async def handle_crisis(founder_name: str, startup_name: str):
    """
    Immediately:
    1. Sends mental health resources to founder in #founder-updates
    2. Alerts ops team in #ops-team
    3. Logs to WellnessAlerts table in Airtable (dashboard reads this)
    """
    from agents.crisis import get_crisis_founder_message
    from memory.store import log_wellness_alert

    for guild in bot.guilds:
        # 1. Send resources to founder immediately — no approval needed
        founder_channel = discord.utils.get(
            guild.channels, name="founder-updates"
        )
        if founder_channel:
            await founder_channel.send(
                get_crisis_founder_message(founder_name)
            )
            print(f"✅ Wellness resources sent to {founder_name}")

        # 2. Alert the ops team immediately
        ops_channel = discord.utils.get(guild.channels, name="ops-team")
        if ops_channel:
            await ops_channel.send(
                f"🚨 **Wellness Alert — Immediate Attention Needed**\n"
                f"**Founder:** {founder_name}\n"
                f"**Startup:** {startup_name}\n"
                f"A message was flagged as a potential mental health concern. "
                f"The founder has been sent crisis resources. "
                f"Please follow up with them personally as soon as possible."
            )
            print(f"✅ Ops team alerted for {founder_name}")

    # 3. Log to Airtable so dashboard shows the wellness alert card
    log_wellness_alert(founder_name, startup_name)


@bot.event
async def on_ready():
    print(f"✅ Founder OS live as {bot.user}")
    tree.copy_global_to(guild=MY_GUILD)
    synced = await tree.sync(guild=MY_GUILD)
    print(f"✅ Synced {len(synced)} slash commands to guild")
    start_scheduler()
    flask_thread = threading.Thread(
        target=lambda: webhook.app.run(port=5000, use_reloader=False)
    )
    flask_thread.daemon = True
    flask_thread.start()
    print("✅ Webhook server running on port 5000")

@bot.event
async def on_resumed():
    print("🔄 Discord connection resumed — all good")

@tree.command(
    name="register",
    description="Register your startup with Founder OS",
    guild=MY_GUILD
)
@app_commands.describe(
    startup_name="Your startup's name",
    stage="Your current stage"
)
@app_commands.choices(stage=[
    app_commands.Choice(name="Idea", value="idea"),
    app_commands.Choice(name="MVP", value="mvp"),
    app_commands.Choice(name="Growth", value="growth"),
    app_commands.Choice(name="Scaling", value="scaling"),
])
async def register(
    interaction: discord.Interaction,
    startup_name: str,
    stage: app_commands.Choice[str]
):
    founder_name = interaction.user.display_name
    guild = interaction.guild

    existing_role = discord.utils.get(guild.roles, name=startup_name)
    if not existing_role:
        role = await guild.create_role(name=startup_name)
    else:
        role = existing_role

    await interaction.user.add_roles(role)

    upsert_profile(founder_name, {
        "stage": stage.value,
        "blockers": [],
        "wins": [],
        "sentiment": "neutral",
        "needs_resource": False,
        "resource_type": None,
        "startup_name": startup_name,
        "registered_at": datetime.now().isoformat()
    })

    await interaction.response.send_message(
        f"✅ Welcome {founder_name}! **{startup_name}** is now registered at "
        f"the **{stage.value}** stage. Post updates anytime in #founder-updates.",
        ephemeral=True
    )

    welcome_channel = discord.utils.get(guild.channels, name="founder-updates")
    if welcome_channel:
        await welcome_channel.send(
            f"👋 Welcome **{founder_name}** and **{startup_name}** to The Foundry! "
            f"Feel free to share updates, wins, blockers, or questions here anytime."
        )

    print(f"✅ Registered {founder_name} → {startup_name} ({stage.value})")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.channel.name != "founder-updates":
        return
    if message.content.startswith("/"):
        return

    founder_name = message.author.display_name

    # Get startup name from Discord role
    startup_name = "Unknown"
    for role in message.author.roles:
        if role.name != "@everyone" and not role.name.startswith("Foundry"):
            startup_name = role.name
            break

    # React immediately so founder knows the message was received
    await message.add_reaction("✅")

    # --- Buffer logic ---
    if founder_name in message_buffer:
        # Founder already has a pending buffer — cancel the existing timer
        # and add this message to the existing buffer
        message_buffer[founder_name]["timer"].cancel()
        message_buffer[founder_name]["messages"].append(message.content)
        print(f"➕ Buffered message {len(message_buffer[founder_name]['messages'])} from {founder_name}")
    else:
        # First message from this founder — create a new buffer entry
        message_buffer[founder_name] = {
            "messages": [message.content],
            "startup_name": startup_name
        }
        print(f"🕐 Started buffer for {founder_name}")

    # Set a new timer — if no more messages arrive in BUFFER_WINDOW_SECONDS,
    # process everything in the buffer
    loop = asyncio.get_event_loop()
    timer = threading.Timer(
        BUFFER_WINDOW_SECONDS,
        lambda: asyncio.run_coroutine_threadsafe(
            process_buffer(founder_name), loop
        )
    )
    timer.start()
    message_buffer[founder_name]["timer"] = timer


bot.run(DISCORD_TOKEN)