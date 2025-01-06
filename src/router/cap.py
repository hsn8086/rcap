import asyncio
from fastapi import APIRouter, HTTPException

from ..tasker import tasker, Status, Ticket

router = APIRouter()


@router.get("/submit")
async def submit(num: int):
    tasker.submit(num)
    asyncio.create_task(tasker.process())
    return


@router.get("/status", response_model=Status)
async def status():
    return tasker.status()


@router.get("/get_ticket", response_model=Ticket)
async def get_ticket():
    try:
        return next(tasker.get_ticket())
    except (StopIteration, RuntimeError):
        raise HTTPException(status_code=404, detail="No ticket available")
