from fastapi import FastAPI
import uvicorn
from starlette.responses import PlainTextResponse

from backend.app.config import host, port
from backend.app.database import init_db
from backend.app.routes import api_router

app = FastAPI()
app.include_router(api_router)


@app.on_event("startup")
def startup_event():
    init_db()


@app.get("/api/ping", response_class=PlainTextResponse)
async def ping():
    return "ok"


if __name__ == "__main__":
    uvicorn.run(app, host=host, port=int(port), reload=True)
