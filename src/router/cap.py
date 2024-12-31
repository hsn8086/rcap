import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..tasker import tasker

router = APIRouter()


class Status(BaseModel):
    processing: int
    tickets: int


@router.get("/submit")
async def submit(num: int):
    tasker.submit(num)
    asyncio.create_task(tasker.process())
    return


@router.get("/status")
async def status():
    num_of_process, num_of_tickets = tasker.status()
    return Status(processing=num_of_process, tickets=num_of_tickets)


@router.get("/get_ticket")
async def get_ticket():
    try:
        return next(tasker.get_ticket())
    except (StopIteration,RuntimeError):
        raise HTTPException(status_code=404, detail="No ticket available")
