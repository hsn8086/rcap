import uvicorn
import uvicorn.logging
uvicorn.logging
uvicorn.run("src.main:app", host="0.0.0.0", port=8000,log_config=None)