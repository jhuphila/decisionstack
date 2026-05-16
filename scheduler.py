from apscheduler.schedulers.asyncio import AsyncIOScheduler
from memory.store import get_all_profiles, update_health_status
from agents.reasoning import reason
from agents.action import handle_action

scheduler = AsyncIOScheduler()


async def proactive_scan():
    print("Running proactive scan...")
    profiles = get_all_profiles()

    for record in profiles:
        founder_name = record["fields"].get("founder_name")
        if not founder_name:
            continue

        decision = await reason(founder_name, record)
        print(f"  🔍 {founder_name}: tier {decision.get('tier')} | health {decision['health_status']}")

        # Always update health status regardless of tier
        update_health_status(founder_name, decision["health_status"])

        if decision.get("tier", 1) != 1:
            await handle_action(decision)
            print(f"  → Action handled for {founder_name}")


def start_scheduler():
    # Only add the job if it doesn't already exist
    if not scheduler.get_job('proactive_scan'):
        scheduler.add_job(
            proactive_scan,
            'interval',
            hours=24,
            id='proactive_scan'
        )
        print("Scheduler running — proactive scan every 24 hours")

    # Only start if not already running
    if not scheduler.running:
        scheduler.start()