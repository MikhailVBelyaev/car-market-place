"""
Shared utilities for all OLX scrapers:
  - RunTracker  : POST start / PATCH progress / PATCH finish to Django API
  - human_sleep : random delay with occasional long "reading" pauses
  - EARLY_STOP_THRESHOLD : stop pagination when N consecutive pages have 0 new ads
"""

import os
import time
import random
import logging

import requests

logger = logging.getLogger(__name__)

DJANGO_URL = os.environ.get('DJANGO_URL', 'http://django:8000')
RUNS_URL   = f"{DJANGO_URL.rstrip('/')}/api/scraper-runs/"

EARLY_STOP_THRESHOLD = int(os.environ.get('EARLY_STOP_PAGES', '2'))


# ---------------------------------------------------------------------------
# Human-like delay
# ---------------------------------------------------------------------------
def human_sleep(base_min: float = 1.0, base_max: float = 2.5):
    """
    Sleep a random interval.  10 % of the time add a longer 'reading' pause
    (4–10 s) to avoid fixed-interval bot fingerprinting.
    """
    delay = random.uniform(base_min, base_max)
    if random.random() < 0.10:
        delay += random.uniform(4.0, 10.0)
    time.sleep(delay)


# ---------------------------------------------------------------------------
# Run tracker
# ---------------------------------------------------------------------------
class RunTracker:
    """
    Thin client that keeps a Django scraper_runs row up to date.

    Usage:
        tracker = RunTracker('apartments', category='apartments')
        tracker.start()
        ...
        tracker.update(pages_scraped=5, new_records=120)
        tracker.finish(total_records=260)
        # or on error:
        tracker.finish_error("OLX returned 403")
    """

    def __init__(self, scraper_name: str, category: str | None = None):
        self.scraper_name = scraper_name
        self.category     = category
        self.run_id: int | None = None

    def start(self) -> None:
        try:
            resp = requests.post(RUNS_URL, json={
                'scraper_name': self.scraper_name,
                'category':     self.category,
            }, timeout=10)
            if resp.status_code == 201:
                self.run_id = resp.json()['id']
                logger.info("RunTracker: started run %s for %s/%s",
                            self.run_id, self.scraper_name, self.category)
        except Exception as e:
            logger.warning("RunTracker.start failed: %s", e)

    def update(self, **kwargs) -> None:
        if not self.run_id:
            return
        try:
            requests.patch(f"{RUNS_URL}{self.run_id}/", json=kwargs, timeout=10)
        except Exception as e:
            logger.warning("RunTracker.update failed: %s", e)

    def finish(self, total_records: int = 0, early_stopped: bool = False) -> None:
        from datetime import datetime, timezone
        self.update(
            status='completed',
            total_records=total_records,
            early_stopped=early_stopped,
            finished_at=datetime.now(timezone.utc).isoformat(),
        )

    def finish_error(self, msg: str) -> None:
        from datetime import datetime, timezone
        self.update(
            status='error',
            error_msg=msg[:500],
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
