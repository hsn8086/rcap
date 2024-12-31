from fastapi import APIRouter

from . import cap,rep
routers = APIRouter()
routers.include_router(cap.router, prefix="/cap")
routers.include_router(rep.router, prefix="/rep")