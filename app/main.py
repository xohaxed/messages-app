"""Messages API -- FastAPI entrypoint."""

from contextlib import asynccontextmanager

import psycopg
import psycopg_pool
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .db import check_db, pool
from .models import (
    Message,
    MessageIn,
    create_message,
    delete_message,
    list_messages,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open()
    yield
    pool.close()


app = FastAPI(title="Messages API", version="0.2.0", lifespan=lifespan)


@app.exception_handler(psycopg.Error)
async def db_error_handler(request: Request, exc: psycopg.Error):
    """Database failure -> 503, never 500.

    503 means "dependency down, retry shortly". 500 means "this code is
    broken". Load balancers, monitoring and clients treat them very
    differently, and mislabelling an outage as a bug costs real debugging
    time at 3am.
    """
    return JSONResponse(status_code=503, content={"detail": "database unavailable"})


@app.exception_handler(psycopg_pool.PoolTimeout)
async def pool_timeout_handler(request: Request, exc: psycopg_pool.PoolTimeout):
    return JSONResponse(status_code=503, content={"detail": "database unavailable"})


@app.get("/health")
def health():
    """Liveness + dependency check.

    Returns 503 when the database is unreachable. An endpoint that returns
    200 regardless of its dependencies is worse than no endpoint at all: the
    deploy pipeline marks a broken release as successful and the load
    balancer keeps sending it traffic.
    """
    if not check_db():
        raise HTTPException(status_code=503, detail="database unreachable")
    return {"status": "ok", "database": "up"}


@app.get("/messages", response_model=list[Message])
def get_messages():
    return list_messages()


@app.post("/messages", response_model=Message, status_code=201)
def post_message(data: MessageIn):
    return create_message(data)


@app.delete("/messages/{message_id}", status_code=204)
def remove_message(message_id: int):
    if not delete_message(message_id):
        raise HTTPException(status_code=404, detail="message not found")
