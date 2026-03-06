from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database.database import get_db
from app.database.models import Task
from app.core.deps import get_current_user_and_org

router = APIRouter(prefix="/discovery", tags=["Discovery"])

class DiscoveryRunRequest(BaseModel):
    industry: str
    location: str
    limit: Optional[int] = 50

@router.post("/run")
def run_discovery(
    req: DiscoveryRunRequest,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    
    # Use PipelineOrchestrator instead of direct delay
    from app.services.pipeline_orchestrator import PipelineOrchestrator
    task_id = PipelineOrchestrator.start_discovery(
        db, req.industry, req.location, req.limit, str(active_org_id)
    )
    
    return {"message": "Discovery pipeline started", "task_id": task_id}

@router.get("/status/{task_id}")
def get_discovery_status(
    task_id: str,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    current_user, active_org_id, role = deps
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    return {
        "task_id": str(task.id),
        "task_name": task.task_name,
        "status": task.status,
        "progress": task.progress,
        "result": task.result,
        "error_message": task.error_message
    }
