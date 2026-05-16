from dotenv import load_dotenv
import os

load_dotenv()

# TODO: Get the tokens and put them as an .env file
# Where to get each key:
#Discord token → discord.com/developers → New Application → Bot → Reset Token
#Anthropic key → console.anthropic.com
#Airtable key → airtable.com → Account → Developer Hub → Personal Access Token


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
DISCORD_GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))
