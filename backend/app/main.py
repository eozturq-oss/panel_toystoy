from fastapi import FastAPI

from .db import Base, engine
from . import models  # noqa: F401

app = FastAPI(title="Toy Marketplace Integration API", version="1.0.0")


@app.on_event("startup")
def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
