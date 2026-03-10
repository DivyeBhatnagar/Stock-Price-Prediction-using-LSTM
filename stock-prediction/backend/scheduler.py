"""
scheduler.py
============
Background scheduler that automatically refreshes stock data at
configurable intervals using APScheduler.

Integrates with LiveDataManager to keep all watched tickers up to date.

Usage (standalone):
    python scheduler.py

Usage (from FastAPI):
    from scheduler import DataScheduler
    sched = DataScheduler(data_dir="path/to/data/raw")
    sched.start()           # non-blocking
    sched.stop()            # on shutdown

Author  : Stock-Prediction AI Pipeline
Version : 1.0.0
"""

import os
import sys
import json
import logging
import threading
from datetime import datetime, time as dtime
from typing import Optional, Dict, List

# Ensure model/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "model"))

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from live_data_manager import LiveDataManager, get_manager

log = logging.getLogger("scheduler")


# ─────────────────────────────────────────────
# DEFAULT SCHEDULE CONFIG
# ─────────────────────────────────────────────

DEFAULT_CONFIG = {
    "enabled":           True,
    "mode":              "interval",      # "interval" | "cron"
    "interval_minutes":  60,              # for interval mode
    "cron_hour":         "16",            # for cron mode (after Indian market close)
    "cron_minute":       "30",
    "cron_day_of_week":  "mon-fri",
    "max_concurrent":    3,               # max tickers refreshed in parallel (unused, sequential for rate limits)
    "auto_add_trained":  True,            # auto-add trained tickers to watchlist
}


class DataScheduler:
    """
    Wraps APScheduler to periodically refresh stock data via LiveDataManager.
    """

    def __init__(
        self,
        data_dir: str = None,
        config: Dict = None,
    ):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
        self.data_dir = os.path.abspath(data_dir)

        self.config   = {**DEFAULT_CONFIG, **(config or {})}
        self.manager  = get_manager(self.data_dir)
        self._scheduler: Optional[BackgroundScheduler] = None
        self._history: List[Dict] = []   # last N run results
        self._max_history = 50
        self._lock = threading.Lock()

        self._config_path = os.path.join(self.data_dir, "scheduler_config.json")
        self._load_config()

    # ─── Config persistence ──────────────────

    def _load_config(self):
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path) as f:
                    saved = json.load(f)
                self.config.update(saved.get("config", {}))
                self._history = saved.get("history", [])[-self._max_history:]
                log.info(f"[Scheduler] Loaded config: mode={self.config['mode']}, "
                         f"interval={self.config['interval_minutes']}min")
            except Exception as e:
                log.warning(f"[Scheduler] Failed to load config: {e}")

    def _save_config(self):
        data = {
            "config":   self.config,
            "history":  self._history[-self._max_history:],
            "saved_at": datetime.now().isoformat(),
        }
        try:
            with open(self._config_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            log.warning(f"[Scheduler] Failed to save config: {e}")

    # ─── Scheduler lifecycle ─────────────────

    def start(self):
        """Start the background scheduler."""
        if self._scheduler and self._scheduler.running:
            log.info("[Scheduler] Already running.")
            return

        if not self.config.get("enabled", True):
            log.info("[Scheduler] Disabled by config, not starting.")
            return

        self._scheduler = BackgroundScheduler(
            job_defaults={"coalesce": True, "max_instances": 1}
        )

        # Add the job based on mode
        if self.config["mode"] == "cron":
            trigger = CronTrigger(
                hour=self.config["cron_hour"],
                minute=self.config["cron_minute"],
                day_of_week=self.config["cron_day_of_week"],
            )
            self._scheduler.add_job(
                self._refresh_job, trigger, id="data_refresh", replace_existing=True
            )
            log.info(f"[Scheduler] Started — cron mode: "
                     f"{self.config['cron_hour']}:{self.config['cron_minute']} "
                     f"({self.config['cron_day_of_week']})")
        else:
            trigger = IntervalTrigger(minutes=self.config["interval_minutes"])
            self._scheduler.add_job(
                self._refresh_job, trigger, id="data_refresh", replace_existing=True
            )
            log.info(f"[Scheduler] Started — interval mode: "
                     f"every {self.config['interval_minutes']} minutes")

        self._scheduler.start()

    def stop(self):
        """Stop the scheduler gracefully."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            log.info("[Scheduler] Stopped.")

    def is_running(self) -> bool:
        return self._scheduler is not None and self._scheduler.running

    def reschedule(self, **kwargs):
        """
        Update schedule config and restart.

        Accepted kwargs: mode, interval_minutes, cron_hour, cron_minute,
                         cron_day_of_week, enabled
        """
        self.config.update(kwargs)
        self._save_config()

        if self._scheduler and self._scheduler.running:
            self.stop()

        if self.config.get("enabled", True):
            self.start()

        return self.get_status()

    # ─── The actual refresh job ──────────────

    def _refresh_job(self):
        """Called by APScheduler — refreshes all watched tickers."""
        log.info("[Scheduler] ⏰ Scheduled refresh starting …")
        start = datetime.now()

        try:
            # If auto_add_trained is on, add any trained tickers not in watchlist
            if self.config.get("auto_add_trained", True):
                self._auto_add_trained()

            result = self.manager.refresh_all_watched(force=False)
            duration = (datetime.now() - start).total_seconds()

            entry = {
                "timestamp": start.isoformat(),
                "duration_sec": round(duration, 1),
                "total": result["total"],
                "refreshed": result["refreshed"],
                "errors": result["errors"],
                "trigger": "scheduled",
            }

            with self._lock:
                self._history.append(entry)
                self._history = self._history[-self._max_history:]

            self._save_config()
            log.info(f"[Scheduler] Refresh done in {duration:.1f}s — "
                     f"{result['refreshed']}/{result['total']} OK")
        except Exception as e:
            log.error(f"[Scheduler] Refresh job failed: {e}", exc_info=True)
            entry = {
                "timestamp": start.isoformat(),
                "error": str(e),
                "trigger": "scheduled",
            }
            with self._lock:
                self._history.append(entry)
            self._save_config()

    def _auto_add_trained(self):
        """Add any tickers with trained models to the watchlist."""
        model_dir = os.path.join(os.path.dirname(__file__), "models")
        if not os.path.isdir(model_dir):
            return
        for d in os.listdir(model_dir):
            cfg = os.path.join(model_dir, d, "config.json")
            if os.path.isfile(cfg) and d not in self.manager.get_watchlist():
                self.manager.add_to_watchlist(d)
                log.info(f"[Scheduler] Auto-added trained ticker: {d}")

    # ─── Manual trigger ──────────────────────

    def trigger_now(self, tickers: Optional[List[str]] = None) -> Dict:
        """
        Manually trigger a data refresh (not waiting for schedule).
        If tickers is None, refreshes all watched tickers.
        """
        start = datetime.now()

        if tickers:
            results = {}
            errors = []
            for t in tickers:
                r = self.manager.refresh_ticker(t, force=True)
                results[t] = r
                if r.get("action") == "error":
                    errors.append(t)
            result = {
                "total": len(tickers),
                "refreshed": len(tickers) - len(errors),
                "errors": errors,
                "results": results,
            }
        else:
            result = self.manager.refresh_all_watched(force=True)

        duration = (datetime.now() - start).total_seconds()
        entry = {
            "timestamp": start.isoformat(),
            "duration_sec": round(duration, 1),
            "total": result.get("total", 0),
            "refreshed": result.get("refreshed", 0),
            "errors": result.get("errors", []),
            "trigger": "manual",
        }
        with self._lock:
            self._history.append(entry)
            self._history = self._history[-self._max_history:]
        self._save_config()

        return {**result, "duration_sec": round(duration, 1)}

    # ─── Status / introspection ──────────────

    def get_status(self) -> Dict:
        """Return current scheduler status + config."""
        next_run = None
        if self._scheduler and self._scheduler.running:
            jobs = self._scheduler.get_jobs()
            if jobs:
                next_run = str(jobs[0].next_run_time)

        return {
            "running":        self.is_running(),
            "config":         self.config,
            "next_run":       next_run,
            "watchlist":      self.manager.get_watchlist(),
            "history_count":  len(self._history),
            "last_run":       self._history[-1] if self._history else None,
        }

    def get_history(self, limit: int = 20) -> List[Dict]:
        """Return recent refresh history."""
        return self._history[-limit:]


# ─────────────────────────────────────────────
# SINGLETON
# ─────────────────────────────────────────────

_scheduler_instance: Optional[DataScheduler] = None

def get_scheduler(data_dir: str = None) -> DataScheduler:
    """Get or create the singleton DataScheduler."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = DataScheduler(data_dir=data_dir)
    return _scheduler_instance


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Stock data scheduler")
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--mode", choices=["interval", "cron"], default="interval")
    parser.add_argument("--interval", type=int, default=60, help="Interval in minutes")
    parser.add_argument("--once", action="store_true", help="Refresh once and exit")
    args = parser.parse_args()

    sched = get_scheduler(args.data_dir)
    sched.config["mode"] = args.mode
    sched.config["interval_minutes"] = args.interval

    if args.once:
        print("Running one-time refresh …")
        result = sched.trigger_now()
        print(json.dumps(result, indent=2, default=str))
    else:
        sched.start()
        print(f"Scheduler running ({args.mode} mode). Press Ctrl+C to stop.")
        try:
            import signal
            signal.pause()
        except (KeyboardInterrupt, SystemExit):
            sched.stop()
