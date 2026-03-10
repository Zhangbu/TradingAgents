"""
System API routes - config, logs, tasks, status.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import time

from ..database import get_db, SystemConfig, ScheduledTask, SystemLog, Signal, Position
from ..schemas import (
    ConfigUpdateRequest, ConfigResponse,
    TaskCreateRequest, TaskResponse,
    LogResponse, SystemStatusResponse,
    SuccessResponse
)

router = APIRouter(prefix="/system", tags=["System"])

# Track system start time
START_TIME = time.time()


# ==================== Status ====================

@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status(db: Session = Depends(get_db)):
    """Get system status."""
    # Get counts
    pending_signals = db.query(Signal).filter(Signal.status == "pending").count()
    open_positions = db.query(Position).filter(Position.status == "open").count()
    
    # Get latest log
    latest_log = db.query(SystemLog).order_by(SystemLog.created_at.desc()).first()
    last_analysis = None
    if latest_log and latest_log.module == "analysis":
        last_analysis = latest_log.created_at
    
    # Calculate daily PnL (simplified)
    today = datetime.utcnow().date()
    daily_pnl = 0.0  # TODO: Calculate from closed positions today
    
    return SystemStatusResponse(
        status="running",
        mode="paper",  # TODO: Get from config
        uptime=time.time() - START_TIME,
        last_analysis=last_analysis,
        pending_signals=pending_signals,
        open_positions=open_positions,
        daily_pnl=daily_pnl
    )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ==================== Configuration ====================

@router.get("/config", response_model=List[ConfigResponse])
async def list_config(db: Session = Depends(get_db)):
    """List all configuration values."""
    configs = db.query(SystemConfig).all()
    return configs


@router.get("/config/{key}", response_model=ConfigResponse)
async def get_config(key: str, db: Session = Depends(get_db)):
    """Get a specific configuration value."""
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config


@router.put("/config", response_model=ConfigResponse)
async def update_config(update: ConfigUpdateRequest, db: Session = Depends(get_db)):
    """Update or create a configuration value."""
    config = db.query(SystemConfig).filter(SystemConfig.key == update.key).first()
    
    if config:
        config.value = update.value
        if update.description:
            config.description = update.description
    else:
        config = SystemConfig(
            key=update.key,
            value=update.value,
            description=update.description
        )
        db.add(config)
    
    db.commit()
    db.refresh(config)
    return config


@router.delete("/config/{key}", response_model=SuccessResponse)
async def delete_config(key: str, db: Session = Depends(get_db)):
    """Delete a configuration value."""
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    db.delete(config)
    db.commit()
    return SuccessResponse(message=f"Configuration '{key}' deleted")


# ==================== Scheduled Tasks ====================

@router.get("/tasks", response_model=List[TaskResponse])
async def list_tasks(db: Session = Depends(get_db)):
    """List all scheduled tasks."""
    tasks = db.query(ScheduledTask).all()
    return tasks


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, db: Session = Depends(get_db)):
    """Get a specific scheduled task."""
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/tasks", response_model=TaskResponse)
async def create_task(task: TaskCreateRequest, db: Session = Depends(get_db)):
    """Create a new scheduled task."""
    db_task = ScheduledTask(
        name=task.name,
        task_type=task.task_type.value,
        schedule=task.schedule,
        config=json.dumps(task.config) if task.config else None
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@router.put("/tasks/{task_id}/enable", response_model=TaskResponse)
async def enable_task(task_id: int, db: Session = Depends(get_db)):
    """Enable a scheduled task."""
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.enabled = True
    db.commit()
    db.refresh(task)
    return task


@router.put("/tasks/{task_id}/disable", response_model=TaskResponse)
async def disable_task(task_id: int, db: Session = Depends(get_db)):
    """Disable a scheduled task."""
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.enabled = False
    db.commit()
    db.refresh(task)
    return task


@router.delete("/tasks/{task_id}", response_model=SuccessResponse)
async def delete_task(task_id: int, db: Session = Depends(get_db)):
    """Delete a scheduled task."""
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.delete(task)
    db.commit()
    return SuccessResponse(message=f"Task {task_id} deleted")


# ==================== Logs ====================

@router.get("/logs", response_model=List[LogResponse])
async def list_logs(
    level: Optional[str] = Query(None, description="Filter by level"),
    module: Optional[str] = Query(None, description="Filter by module"),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db)
):
    """List system logs."""
    query = db.query(SystemLog)
    
    if level:
        query = query.filter(SystemLog.level == level)
    if module:
        query = query.filter(SystemLog.module == module)
    
    return query.order_by(SystemLog.created_at.desc()).limit(limit).all()


@router.delete("/logs", response_model=SuccessResponse)
async def clear_logs(
    before_days: int = Query(7, description="Clear logs older than N days"),
    db: Session = Depends(get_db)
):
    """Clear old system logs."""
    cutoff = datetime.utcnow() - timedelta(days=before_days)
    deleted = db.query(SystemLog).filter(SystemLog.created_at < cutoff).delete()
    db.commit()
    return SuccessResponse(message=f"Cleared {deleted} log entries")


from datetime import timedelta