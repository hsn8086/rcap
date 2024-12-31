from fastapi import APIRouter

from . import cap
routers = APIRouter()
routers.include_router(cap.router, prefix="/cap")