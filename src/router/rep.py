import asyncio
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from ..tasker import tasker

router = APIRouter()


@router.get("/index")
async def index():
    with open("index.html") as f:
        return Response(
            content=f.read(),
            media_type="text/html",
        )

