"""
scheduler.py - Refresh the user data every week.
"""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.database import get_users_collection
from app.services.spotify import pull_user_data, refresh_token

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _refresh_all_users() -> None:
    """
    Iterate over all users with is_spotify_connected=True and for each:
      1. Refresh the access_token
      2. Re-pull Spotify music data

    A failure on one user does not interrupt processing of the remaining users.
    """
    users_col = get_users_collection()

    # Fetch only the fields we need to reduce data transfer
    cursor = users_col.find(
        {"is_spotify_connected": True},
        {"_id": 1},
    )

    user_ids: list[str] = []
    async for doc in cursor:
        user_ids.append(str(doc["_id"]))

    logger.info("[Scheduler] Starting weekly refresh for %d users", len(user_ids))

    success, failed = 0, 0
    for user_id in user_ids:
        try:
            new_token = await refresh_token(user_id)
            await pull_user_data(user_id=user_id, access_token=new_token)
            success += 1
        except Exception as exc:
            failed += 1
            logger.error(
                "[Scheduler] Failed to refresh user %s: %s", user_id, exc
            )

    logger.info(
        "[Scheduler] Weekly refresh complete: %d succeeded, %d failed",
        success,
        failed,
    )


def start_scheduler() -> None:
    """
    Initialize and start APScheduler to run a full refresh every 7 days.

    Should be called once in the FastAPI app's startup event.
    """
    global _scheduler

    if _scheduler is not None:
        logger.warning("[Scheduler] Already running, skipping start")
        return

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _refresh_all_users,
        trigger=IntervalTrigger(weeks=1),
        id="weekly_spotify_refresh",
        replace_existing=True,
        max_instances=1,        # Prevent overlapping runs if the previous job is still running
        misfire_grace_time=3600,  # Allow up to 1 hour to fire a missed job
    )
    _scheduler.start()
    logger.info("[Scheduler] Weekly Spotify refresh job started")


def stop_scheduler() -> None:
    """
    Gracefully shut down the scheduler. Called in the FastAPI app's shutdown event.
    """
    global _scheduler

    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("[Scheduler] Stopped")