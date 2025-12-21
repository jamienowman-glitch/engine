"""Standalone FastAPI App for BBK Preview."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from engines.bot_better_know.preview_routes import router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
