from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import connect_db, disconnect_db, setup_db
from routes.auth import router as auth_router
from routes.manga import router as manga_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    await setup_db()
    yield
    await disconnect_db()


app = FastAPI(title="ACP App API", lifespan=lifespan)
app.include_router(auth_router, prefix="/api")
app.include_router(manga_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "BIT.MANGA API"}
