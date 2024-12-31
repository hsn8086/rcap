
import fastapi

from .router import routers

app = fastapi.FastAPI()
app.include_router(routers, prefix="/api/v1")
