# DecisionStack
### Agentic AI Infrastructure for Startup Community Management

Built for The Foundry × WiCS Case Competition @ Drexel University.

DecisionStack is an agentic AI operations layer that ensures no startup founder slips through the cracks. It proactively monitors founder activity across Discord, builds a living intelligence profile for each startup, and autonomously routes messages to the right level of response — from immediate advice to operator escalation.

---

## What It Does

When a founder posts in `#founder-updates`, the system:

1. **Buffers** rapid-fire messages (15s window) and combines them into one before processing
2. **Crisis checks** the message first — if a wellness concern is detected, resources are sent immediately and operators are alerted
3. **Ingests** the message using Claude to extract structured data (stage, blockers, wins, sentiment)
4. **Updates memory** in Airtable — blockers accumulate over time and are intelligently resolved when founders report fixes
5. **Reasons** over the full profile + latest message and classifies into one of three tiers:
   - **Tier 1** — No action needed, bot stays silent
   - **Tier 2** — General advice sent immediately, no operator involvement
   - **Tier 3** — Serious blocker, queues an action card on the operator dashboard for approval
6. **Acts** — on approval, sends the founder a message in Discord AND posts operator tasks to `#ops-team`

A **24-hour proactive scanner** also runs automatically, checking all registered startups for silence and health status changes — even if a founder never posts.

---

## System Architecture

```
Discord #founder-updates
        ↓
  Message Buffer (15s)
        ↓
  Crisis Agent ──── YES ──→ Send resources to founder + alert #ops-team
        ↓ NO
  Ingestion Agent (Claude)
  Extracts: stage, blockers, wins, resolved_blockers, sentiment
        ↓
  Memory Store (Airtable — Startups table)
  Merges blockers, resolves stale ones via Claude
        ↓
  Reasoning Agent (Claude)
  Classifies tier based on latest message + profile
        ↓
  Action Agent
  Tier 1 → silent
  Tier 2 → immediate Discord message
  Tier 3 → Airtable ActionQueue + ping #ops-team
        ↓
  Lovable Operator Dashboard
  Operator reviews → clicks Approve
        ↓
  Webhook (Flask /approve)
  → Bot message sent to founder in #founder-updates
  → Operator tasks posted to #ops-team
```

---

## Project Structure

```
decisionstack/
├── .env                    ← your secrets (never committed)
├── .env.example            ← template for teammates
├── .gitignore
├── requirements.txt
├── bot_instance.py         ← shared Discord bot object
├── config.py               ← loads environment variables
├── main.py                 ← entry point — bot + Flask + scheduler
├── scheduler.py            ← 24hr proactive scan
├── webhook.py              ← Flask /approve endpoint
├── agents/
│   ├── __init__.py
│   ├── action.py           ← handles tier routing + Airtable queue
│   ├── crisis.py           ← wellness alert detection + response
│   ├── ingestion.py        ← Claude extracts structured data from messages
│   └── reasoning.py        ← Claude decides tier + drafts response
└── memory/
    ├── __init__.py
    └── store.py            ← all Airtable read/write operations
```

---

## Prerequisites

- Python 3.10+
- A Discord account and server you own
- An Anthropic account (console.anthropic.com)
- An Airtable account (airtable.com)
- ngrok installed (ngrok.com/download)

---

## Step 1 — Clone and Install

```bash
git clone https://github.com/YOUR_USERNAME/decisionstack.git
cd decisionstack

python -m venv venv

# Mac/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

pip install -r requirements.txt
```

---

## Step 2 — Discord Setup

### Create the bot
1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. Click **New Application** → give it a name (e.g. "DecisionStack")
3. Go to **Bot** in the left sidebar
4. Click **Reset Token** → copy the token — this is your `DISCORD_TOKEN`
5. Under **Privileged Gateway Intents**, enable:
   - **Message Content Intent**
   - **Server Members Intent**

### Invite the bot to your server
1. Go to **OAuth2** → **URL Generator**
2. Under Scopes, check: `bot`, `applications.commands`
3. Under Bot Permissions, check:
   - `Send Messages`
   - `Read Messages / View Channels`
   - `Add Reactions`
   - `Manage Roles`
4. Copy the generated URL → open it in your browser → select your server

### Set up your Discord server channels
Create these two channels — names must match exactly:
- `#founder-updates` — where founders post their updates
- `#ops-team` — private channel for operators only

### Get your Server ID
1. In Discord: **Settings → Advanced → Developer Mode** → toggle ON
2. Right-click your server name in the left sidebar → **Copy Server ID**
3. This is your `DISCORD_GUILD_ID`

### Give the bot Manage Roles permission
1. Server Settings → Roles → find the bot's role → enable **Manage Roles**
2. Drag the bot's role to the **top** of the role list (it must sit above any roles it will create for founders)

---

## Step 3 — Airtable Setup

Go to [airtable.com](https://airtable.com), create a new base called **"DecisionStack"**, and create these three tables with the exact field names listed:

### Table 1: `Startups`
| Field Name | Field Type |
|---|---|
| `founder_name` | Single line text (Primary) |
| `startup_name` | Single line text |
| `stage` | Single select: `idea`, `mvp`, `growth`, `scaling` |
| `blockers` | Long text |
| `wins` | Long text |
| `sentiment` | Single select: `positive`, `neutral`, `struggling` |
| `last_seen` | Single line text |
| `interaction_count` | Number |
| `health_status` | Single select: `healthy`, `at-risk`, `silent` |

### Table 2: `ActionQueue`
| Field Name | Field Type |
|---|---|
| `founder_name` | Single line text (Primary) |
| `startup_name` | Single line text |
| `action_type` | Single line text |
| `draft_message` | Long text |
| `reasoning` | Long text |
| `resource_suggestion` | Single line text |
| `operator_tasks` | Long text |
| `status` | Single select: `PENDING`, `APPROVED`, `REJECTED` |
| `created_at` | Single line text |

### Table 3: `WellnessAlerts`
| Field Name | Field Type |
|---|---|
| `founder_name` | Single line text (Primary) |
| `startup_name` | Single line text |
| `triggered_at` | Single line text |
| `status` | Single select: `ACTIVE`, `ACKNOWLEDGED` |

### Get your Airtable credentials
- **Base ID** — found in the URL when you're inside your base: `airtable.com/YOUR_BASE_ID/...`
- **API Key** — go to [airtable.com/create/tokens](https://airtable.com/create/tokens) → Create token → grant `data.records:read` and `data.records:write` scopes on your base

---

## Step 4 — Anthropic API Key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. **API Keys** → **Create Key** → copy it
3. This is your `ANTHROPIC_API_KEY`

---

## Step 5 — Environment Variables

```bash
cp .env.example .env
```

Open `.env` and fill in all five values:

```
DISCORD_TOKEN=your_discord_bot_token_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
AIRTABLE_API_KEY=your_airtable_personal_access_token_here
AIRTABLE_BASE_ID=your_airtable_base_id_here
DISCORD_GUILD_ID=your_discord_server_id_here
```

---

## Step 6 — Run the Bot

```bash
python main.py
```

You should see:
```
✅ DecisionStack live as YourBot#1234
✅ Synced 1 slash commands to guild
Scheduler running — proactive scan every 24 hours
✅ Webhook server running on port 5000
```

---

## Step 7 — ngrok Setup

ngrok creates a public tunnel to your local Flask server so the Lovable
dashboard can reach it from the internet.

### Install ngrok
1. Go to [ngrok.com/download](https://ngrok.com/download) and create a free account
2. Download the version for your OS
3. For Windows: extract the `.exe` file somewhere simple like `C:\ngrok\`

### Authenticate ngrok (one time only)
1. After signing up, go to [dashboard.ngrok.com](https://dashboard.ngrok.com)
2. Copy your authtoken from the dashboard
3. Run this command (replace with your actual token):

```bash
ngrok config add-authtoken YOUR_TOKEN_HERE
```

This only needs to be done once per machine.

### Run ngrok
In a separate terminal from your bot, run:

```bash
ngrok http 5000
```

You'll see:
```bash
Forwarding    https://abc123.ngrok-free.app -> http://localhost:5000
```
Copy that `https://` URL — you'll need it for the Lovable dashboard setup
in Step 8.

**Note:** On the free tier, this URL changes every time you restart ngrok.
Each new session, update the Approve button URL in your Lovable project
(Step 8 covers this). Ngrok paid plans offer a reserved static domain
that never changes.

---

## Step 8 — Operator Dashboard (Lovable)

The dashboard is already built and published. You do not need to build it yourself.

**→ Live dashboard: https://decisionstack-io.lovable.app/**

**→ Remix link (fork your own copy): Click **"Edit with Lovable"** → then click **Remix****

### Who needs to do what

**Scenario A — Teammate sharing the same Airtable base (most common)**

You only need to update the ngrok URL to point to your machine. The Airtable credentials are already set to the shared base and don't need to change.

After remixing, prompt Lovable:
> "Update the Approve button's POST request URL to `https://YOUR-NGROK-URL.ngrok-free.app/approve`"

Republish and you're done.

**Scenario B — Completely independent instance with your own Airtable base**

You need to update three things. After remixing, prompt Lovable:
> "Update this app with the following:
> 1. Replace all Airtable Base ID references with `YOUR_NEW_BASE_ID`
> 2. Replace all Airtable API token references with `YOUR_NEW_AIRTABLE_TOKEN`
> 3. Update the Approve button POST URL to `https://YOUR-NGROK-URL.ngrok-free.app/approve`"

Republish and you're done.

### Each new ngrok session (applies to everyone)

1. Start ngrok: `ngrok http 5000` → copy the new `https://` URL
2. In your Lovable project, prompt: *"Update the Approve button URL to `https://NEW-URL.ngrok-free.app/approve`"*
3. Republish

This takes about 30 seconds and only needs to happen once per session.

---

## Founder Flow (end to end)

```
1. Founder uses /register in any Discord channel
   → Selects startup name and stage
   → Gets a Discord role named after their startup
   → Airtable profile created immediately (silent tracking begins from this moment)
   → Welcome message posted in #founder-updates

2. Founder posts updates in #founder-updates
   → Bot reacts with ✅ immediately
   → Messages within 15 seconds are buffered and combined
   → Tier 1: bot stays silent, profile updated quietly
   → Tier 2: bot replies with practical advice immediately
   → Tier 3: action card appears on operator dashboard pending approval

3. Operator reviews pending card on dashboard → clicks Approve
   → Bot message sent to founder in #founder-updates
   → Operator tasks posted to #ops-team Discord channel
   → Task checklist appears and persists on dashboard
```

---

## Environment Variables Reference

| Variable | Where to get it |
|---|---|
| `DISCORD_TOKEN` | Discord Developer Portal → App → Bot → Reset Token |
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys |
| `AIRTABLE_API_KEY` | airtable.com/create/tokens |
| `AIRTABLE_BASE_ID` | URL of your Airtable base |
| `DISCORD_GUILD_ID` | Right-click server name in Discord (Developer Mode must be on) |

---

## Built With

- [discord.py](https://discordpy.readthedocs.io/) — Discord bot framework
- [Anthropic Claude API](https://docs.anthropic.com/) — AI reasoning, ingestion, crisis detection
- [pyairtable](https://pyairtable.readthedocs.io/) — Airtable read/write
- [Flask](https://flask.palletsprojects.com/) — Webhook server for approve endpoint
- [APScheduler](https://apscheduler.readthedocs.io/) — 24hr proactive scan scheduler
- [ngrok](https://ngrok.com/) — Expose local webhook to Lovable dashboard
- [Lovable](https://lovable.dev/) — Operator dashboard frontend
