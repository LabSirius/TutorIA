"""Administrative endpoints (RF-22)."""
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.gateways.openedx_gateway.sync_service import sync_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


class SyncTriggerResponse(BaseModel):
    task_id: str
    status: str
    dry_run: bool


async def verify_admin(x_admin_token: str = Header(..., alias="X-Admin-Token")) -> str:
    # TODO: replace with proper auth (Open edX JWT / IAM) in a later phase.
    # Fail closed: with no token configured, nobody can trigger a sync.
    if not settings.admin_token:
        raise HTTPException(status_code=403, detail="Admin token is not configured")
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return x_admin_token


async def _run_sync(task_id: str, dry_run: bool) -> None:
    logger.info("Open edX sync task %s started (dry_run=%s)", task_id, dry_run)
    results = await sync_service.sync_all(dry_run=dry_run)
    logger.info("Open edX sync task %s finished: %s", task_id, results)


@router.post("/sync-openedx", response_model=SyncTriggerResponse, status_code=202)
async def trigger_openedx_sync(
    background_tasks: BackgroundTasks,
    dry_run: bool = False,
    _admin: str = Depends(verify_admin),
):
    """Trigger a manual Open edX -> PostgreSQL sync. Returns immediately; the
    sync runs in the background (progress is visible in the logs)."""
    task_id = str(uuid.uuid4())
    background_tasks.add_task(_run_sync, task_id, dry_run)
    return SyncTriggerResponse(task_id=task_id, status="accepted", dry_run=dry_run)
