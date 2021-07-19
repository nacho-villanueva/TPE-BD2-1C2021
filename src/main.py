import asyncio

from aioredis import create_redis_pool
from aioredis.pubsub import Receiver
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

from src.pokemon import pokemon_router
from src.player import player_router
from src.configurations import *

app = FastAPI(
    title="Pokemon GO",
    description="Pokemon GO API. College Project for Data Base II.",
    version="1.0.0")

app.include_router(player_router)
app.include_router(pokemon_router)


async def reader(channel):
    async for ch, message in channel.iter():
        print("Got message in channel:", ch, ":", message)


@app.on_event("startup")
async def startup_event():
    app.state.mongodb = AsyncIOMotorClient(MONGODB_URI)
    app.state.redis = await create_redis_pool(REDIS_URI)

    # Set Redis config to notify on Key Expired
    await app.state.redis.config_set("notify-keyspace-events", "Ex")

    ch, = await app.state.redis.psubscribe('__key*__:expired')
    asyncio.get_running_loop().create_task(reader(ch))


@app.on_event("shutdown")
async def shutdown_event():
    app.state.redis.close()
