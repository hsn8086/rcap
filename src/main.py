from pathlib import Path
import fastapi

from loguru import logger
from .router import routers

p = Path("data/logs")
p.mkdir(parents=True, exist_ok=True)

logger.add(p / "info.log", rotation="1 day", retention="7 days", level="INFO")
logger.add(p / "debug.log", rotation="1 day", retention="7 days", level="DEBUG")

app = fastapi.FastAPI()


@app.middleware("http")
async def log_request_params(request: fastapi.Request, call_next):
    # 172.22.0.1:39312 - "GET /api/v1/cap/submit?num=1 HTTP/1.1" 200 OK
    assert request.client

    response = await call_next(request)
    response: fastapi.Response
    logger.info(
        f"{request.client.host}:{request.client.port} - \"{request.method} {request.url} {request.scope['http_version']}\" {response.status_code}"
    )
    return response


app.include_router(routers, prefix="/api/v1")
