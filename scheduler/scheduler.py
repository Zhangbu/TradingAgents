"""
TradingAgents Scheduler - APScheduler-based task scheduling.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from datetime import datetime
import logging
import os

# Configure logging
logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.INFO)

logger = logging.getLogger(__name__)


class TradingScheduler:
    """
    Scheduler for automated trading tasks.
    
    Supports:
    - Scheduled analysis runs
    - Periodic stock scanning
    - Portfolio rebalancing
    - Risk management checks
    """
    
    def __init__(self, db_url: str = None):
        """
        Initialize the scheduler.
        
        Args:
            db_url: Database URL for job storage. Defaults to SQLite.
        """
        if db_url is None:
            db_path = os.path.join(os.path.dirname(__file__), "..", "data", "jobs.db")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            db_url = f"sqlite:///{db_path}"
        
        # Configure job stores
        jobstores = {
            'default': SQLAlchemyJobStore(url=db_url)
        }
        
        # Configure executors
        executors = {
            'default': ThreadPoolExecutor(20)
        }
        
        # Create scheduler
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            timezone='America/New_York'  # Market timezone
        )
        
        self._running = False
    
    def start(self):
        """Start the scheduler."""
        if not self._running:
            self.scheduler.start()
            self._running = True
            logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        if self._running:
            self.scheduler.shutdown()
            self._running = False
            logger.info("Scheduler stopped")
    
    def add_analysis_job(
        self,
        symbol: str,
        cron_expression: str = None,
        interval_minutes: int = None,
        job_id: str = None
    ) -> str:
        """
        Add a scheduled analysis job.
        
        Args:
            symbol: Stock symbol to analyze
            cron_expression: Cron expression for schedule
            interval_minutes: Interval in minutes (alternative to cron)
            job_id: Optional job ID
            
        Returns:
            Job ID
        """
        from .jobs import run_analysis_job
        
        if job_id is None:
            job_id = f"analysis_{symbol}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        if cron_expression:
            trigger = CronTrigger.from_crontab(cron_expression)
        elif interval_minutes:
            trigger = IntervalTrigger(minutes=interval_minutes)
        else:
            # Default: run daily at 9:30 AM ET (market open)
            trigger = CronTrigger(hour=9, minute=30, timezone='America/New_York')
        
        self.scheduler.add_job(
            run_analysis_job,
            trigger=trigger,
            id=job_id,
            args=[symbol],
            name=f"Analysis: {symbol}",
            replace_existing=True
        )
        
        logger.info(f"Added analysis job for {symbol}: {job_id}")
        return job_id
    
    def add_scanner_job(
        self,
        watchlist: list = None,
        cron_expression: str = None,
        interval_minutes: int = 60,
        job_id: str = None
    ) -> str:
        """
        Add a scheduled scanner job.
        
        Args:
            watchlist: List of symbols to scan
            cron_expression: Cron expression for schedule
            interval_minutes: Interval in minutes (default: 60)
            job_id: Optional job ID
            
        Returns:
            Job ID
        """
        from .jobs import run_scanner_job
        
        if job_id is None:
            job_id = f"scanner_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        if cron_expression:
            trigger = CronTrigger.from_crontab(cron_expression)
        else:
            trigger = IntervalTrigger(minutes=interval_minutes)
        
        self.scheduler.add_job(
            run_scanner_job,
            trigger=trigger,
            id=job_id,
            args=[watchlist],
            name="Stock Scanner",
            replace_existing=True
        )
        
        logger.info(f"Added scanner job: {job_id}")
        return job_id
    
    def add_rebalance_job(
        self,
        cron_expression: str = "0 16 * * 1-5",  # 4 PM ET weekdays
        job_id: str = None
    ) -> str:
        """
        Add a portfolio rebalancing job.
        
        Args:
            cron_expression: Cron expression (default: 4 PM ET weekdays)
            job_id: Optional job ID
            
        Returns:
            Job ID
        """
        from .jobs import run_rebalance_job
        
        if job_id is None:
            job_id = f"rebalance_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        trigger = CronTrigger.from_crontab(cron_expression)
        
        self.scheduler.add_job(
            run_rebalance_job,
            trigger=trigger,
            id=job_id,
            name="Portfolio Rebalance",
            replace_existing=True
        )
        
        logger.info(f"Added rebalance job: {job_id}")
        return job_id
    
    def remove_job(self, job_id: str):
        """Remove a scheduled job."""
        self.scheduler.remove_job(job_id)
        logger.info(f"Removed job: {job_id}")
    
    def pause_job(self, job_id: str):
        """Pause a scheduled job."""
        self.scheduler.pause_job(job_id)
        logger.info(f"Paused job: {job_id}")
    
    def resume_job(self, job_id: str):
        """Resume a paused job."""
        self.scheduler.resume_job(job_id)
        logger.info(f"Resumed job: {job_id}")
    
    def get_jobs(self):
        """Get all scheduled jobs."""
        return self.scheduler.get_jobs()
    
    def get_job(self, job_id: str):
        """Get a specific job by ID."""
        return self.scheduler.get_job(job_id)
    
    def run_job_now(self, job_id: str):
        """Trigger a job to run immediately."""
        job = self.scheduler.get_job(job_id)
        if job:
            job.modify(next_run_time=datetime.now())
            logger.info(f"Triggered job: {job_id}")
        else:
            raise ValueError(f"Job not found: {job_id}")


# Global scheduler instance
_scheduler = None


def get_scheduler() -> TradingScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = TradingScheduler()
    return _scheduler