from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.core.deps import get_current_user_and_org
from app.database.models import Task

router = APIRouter(prefix="/tasks", tags=["Pipeline Tasks"])

@router.get("/{task_id}")
async def get_task_status(
    task_id: str,
    deps = Depends(get_current_user_and_org),
    db: Session = Depends(get_db)
):
    """
    Polls the persistent database state of background Celery workflows.
    """
    current_user, active_org_id, role = deps
    
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "id": str(task.id),
        "task_name": task.task_name,
        "status": task.status,
        "progress": task.progress,
        "result": task.result,
        "error_message": task.error_message,
        "updated_at": task.updated_at
    }
