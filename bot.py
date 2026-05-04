import discord
from config import DISCORD_TOKEN

intents = discord.Intents.default()
intents.message_content = True  # Critical — enable this in Discord Dev Portal too

bot = discord.Client(intents=intents)


@bot.event
async def on_ready():
    print(f"Founder OS is live as {bot.user}")


@bot.event
async def on_message(message):
    # Ignore the bot's own messages
    if message.author == bot.user:
        return

    # Only listen in the founder-updates channel
    if message.channel.name == "founder-updates":
        print(f"Received from {message.author.name}: {message.content}")
        # This is where we'll call the ingestion agent (Step 4)


bot.run(DISCORD_TOKEN)