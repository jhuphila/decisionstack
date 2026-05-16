from flask import Flask, request, jsonify
import asyncio
import discord
from bot_instance import bot

app = Flask(__name__)


@app.route("/approve", methods=["POST"])
def handle_approval():
    print("APPROVE ENDPOINT HIT")
    data = request.json
    print(f"Received data: {data}")

    founder_name = data.get("founder_name")
    draft_message = data.get("draft_message")
    operator_tasks = data.get("operator_tasks", "")
    startup_name = data.get("startup_name", "Unknown")

    if not founder_name or not draft_message:
        print("❌ Missing fields")
        return jsonify({"error": "missing fields"}), 400

    print(f"Bot connected: {bot.is_ready()}")

    future = asyncio.run_coroutine_threadsafe(
        send_approved_messages(
            founder_name, draft_message,
            operator_tasks, startup_name
        ),
        bot.loop
    )

    try:
        future.result(timeout=10)
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500


async def send_approved_messages(
    founder_name: str,
    message: str,
    operator_tasks: str,
    startup_name: str
):
    for guild in bot.guilds:
        # 1. Send bot message to founder
        founder_channel = discord.utils.get(
            guild.channels, name="founder-updates"
        )
        if founder_channel:
            await founder_channel.send(f"Hey {founder_name} — {message}")
            print(f"✅ Founder message sent to {founder_name}")

        # 2. Send operator task list to #ops-team
        if operator_tasks:
            ops_channel = discord.utils.get(
                guild.channels, name="ops-team"
            )
            if ops_channel:
                await ops_channel.send(
                    f"📋 **New Operator Tasks — {startup_name}**\n"
                    f"**Founder:** {founder_name}\n\n"
                    f"**Action items:**\n{operator_tasks}"
                )
                print(f"✅ Operator tasks sent to #ops-team")