from aioredis import create_redis_pool
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

from src.pokemon import pokemon_router
from src.player import player_router
from src.configurations import *

app = FastAPI()

app.include_router(player_router)
app.include_router(pokemon_router)


@app.on_event("startup")
async def startup_event():
    app.state.mongodb = AsyncIOMotorClient(MONGODB_URI)
    app.state.redis = await create_redis_pool(REDIS_URI)


@app.on_event("shutdown")
async def shutdown_event():
    app.state.redis.close()
