import asyncio

from aioredis import create_redis_pool
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

from src.demo import demo_router
from src.configurations import *
from src.player import player_router, player_end_session
from src.pokemon import pokemon_router, pokemon_expiration

app = FastAPI(
    title="Pokemon GO",
    description="Pokemon GO API. College Project for Data Base II.",
    version="1.0.0")

app.include_router(player_router)
app.include_router(pokemon_router)
app.include_router(demo_router)


async def reader(channel, state):
    async for ch, message in channel.iter():
        vals = message.decode("utf-8").split(":")
        if len(vals) == 3 and vals[0] == "players" and vals[2] == "expire":
            asyncio.ensure_future(player_end_session(vals[1], state))
        if len(vals) == 4 and vals[0] == "pokemons" and vals[3] == "expire":
            asyncio.ensure_future(pokemon_expiration(vals[1], vals[2], state))


@app.on_event("startup")
async def startup_event():
    app.state.is_running = True

    app.state.mongodb = AsyncIOMotorClient(MONGODB_URI)
    app.state.redis = await create_redis_pool(REDIS_URI)

    # Set Redis config to notify on Key Expired
    await app.state.redis.config_set("notify-keyspace-events", "Ex")

    # Set counters
    await asyncio.wait([
        app.state.redis.set("count:players", 0),
        app.state.redis.set("count:pokemons", 0)
    ])

    ch, = await app.state.redis.psubscribe('__key*__:expired')
    asyncio.get_running_loop().create_task(reader(ch, app.state))


@app.on_event("shutdown")
async def shutdown_event():
    app.state.is_running = False
    app.state.redis.close()
