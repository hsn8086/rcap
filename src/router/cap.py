from re import S
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import fucker
from ..tasker import tasker

router = APIRouter()


class Status(BaseModel):
    num_of_process: int
    num_of_tickets: int


@router.get("/submit")
async def submit(num: int):
    tasker.submit(num)
    return


@router.get("/status")
async def status():
    num_of_process, num_of_tickets = tasker.status()
    return Status(num_of_process=num_of_process, num_of_tickets=num_of_tickets)


@router.get("/get_ticket")
async def get_ticket():
    for ticket in tasker.get_ticket():
        return ticket
    raise HTTPException(status_code=404, detail="No ticket available")
