import asyncio
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import Field
from pydantic.main import BaseModel

from src.configurations import *
from src.level_info import PLAYER_LEVELS
from src.models import CoordinatesModel, PlayerModel
from src.utils import get_distance

# Player will logout after 1 hour = 60 * 60 seconds

player_router = APIRouter(prefix="/player", tags=["Player Requests"])


class NameNCoordsModel(BaseModel):
    player_name: str = Field(..., example="Ash_Ketchum01")
    coordinates: CoordinatesModel


def renew_player_expiration(name, state):
    asyncio.ensure_future(state.redis.expire(f"players:{name}:expire", PLAYER_EXPIRATION))


async def login_player(user, coordinates: CoordinatesModel, state):
    await asyncio.wait([
        state.redis.geoadd("players", coordinates.lat, coordinates.long, user["name"]),
        state.redis.hset(f"players:{user['name']}", "walked_distance", 0),
        state.redis.setex(f"players:{user['name']}:expire", PLAYER_EXPIRATION, "EXPIRE"),
        state.redis.incr("count:players")
    ])


@player_router.post("/")
async def login(user: NameNCoordsModel, request: Request):
    collection = request.app.state.mongodb[MONGODB_DB][MONGODB_PLAYERS_COLLECTION]
    if (player := await collection.find_one({'name': user.player_name})) is not None:
        await login_player(player, user.coordinates, request.app.state)
        return
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user.player_name} not registered")


@player_router.post("/{name}/logout")
async def logout_player(name: str, request: Request):
    await request.app.state.redis.delete(f"players:{name}:expire")
    await player_end_session(name, request.app.state)


@player_router.put("/{name}", status_code=status.HTTP_201_CREATED, response_model=PlayerModel,
                   description="Register a new player.")
async def register_player(name: str, request: Request):
    collection = request.app.state.mongodb[MONGODB_DB][MONGODB_PLAYERS_COLLECTION]
    if await collection.find_one({'name': name}) is None:
        player = {
            'name': name,
            'level': 1,
            'experience': 0,
            'stardust': 0,
            'total_caught': 0,
            'walked_distance': 0,
            'inventory': PLAYER_LEVELS[0]['rewards'],
            'pokemons': []
        }
        collection.insert_one(player)
        return JSONResponse(status_code=status.HTTP_201_CREATED, content=player)
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Player {name} already exists")


def update_mongo_distance(name, walked, state):
    collection = state.mongodb[MONGODB_DB][MONGODB_PLAYERS_COLLECTION]
    collection.update_one({'name': name}, {'$inc': {'walked_distance': walked}})


async def update_distance(old_pos, new_pos, name, state):
    dist = get_distance(old_pos[1], old_pos[0], new_pos.long, new_pos.lat)
    walked = await state.redis.hincrbyfloat(f"players:{name}", "walked_distance", dist)
    if walked > 1:
        state.redis.hset(f"players:{name}", "walked_distance", 0)
        update_mongo_distance(name, walked, state)


@player_router.post("/{name}/move", status_code=status.HTTP_200_OK, description="Move player to new coordinates.")
async def move_player(body: NameNCoordsModel, request: Request):
    old_pos = await request.app.state.redis.geopos("players", body.player_name)
    if len(old_pos) == 1:
        asyncio.ensure_future(
            request.app.state.redis.geoadd("players", body.coordinates.lat, body.coordinates.long, body.player_name))
        asyncio.ensure_future(update_distance(old_pos[0], body.coordinates, body.player_name, request.app.state))
        renew_player_expiration(body.player_name, request.app.state)
        return
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Player {body.player_name} not found")


@player_router.get("/{name}/position", status_code=status.HTTP_200_OK, response_model=CoordinatesModel)
async def get_player_position(name: str, request: Request):
    pos = await request.app.state.redis.geopos("players", name)
    if len(pos) > 0:
        return CoordinatesModel(lat=pos[0][0], long=pos[0][1])
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Player {name} not found")


@player_router.get("/{name}", status_code=status.HTTP_200_OK, response_model=PlayerModel,
                   responses={404: {}, 422: {}})
async def get_player(name: str, request: Request):
    player = await request.app.state.mongodb[MONGODB_DB][MONGODB_PLAYERS_COLLECTION].find_one({'name': name})
    if player is not None:
        return JSONResponse(status_code=status.HTTP_200_OK, content=player)

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Player {name} not found")


async def player_end_session(name, state):
    print(f"Player Session Ended: {name}")
    await state.redis.zrem("players", name)
    walked = float(await state.redis.hget(f"players:{name}", "walked_distance"))
    if walked > 0:
        update_mongo_distance(name, walked, state)
    await state.redis.delete(f"players:{name}")
    await state.redis.decr("count:players")


async def update_player_inventory(player_name, rewards, player_collection):
    player = await player_collection.find_one({"name": player_name})
    inventory = player["inventory"]

    for r in rewards:
        found = False
        for i in inventory:
            if i["item"] == r["item"]:
                i["amount"] += r["amount"]
                found = True
                break
        if not found:
            inventory.append(r)

    return player_collection.update_one({"name": player_name}, {"$set": {"inventory": inventory}})


async def update_player_exp(player_object, increment_exp, state):
    player_collection = state.mongodb[MONGODB_DB][MONGODB_PLAYERS_COLLECTION]
    new_exp = player_object["experience"] + increment_exp
    new_level = player_object["level"]
    if player_object["level"] < MAX_LEVEL and PLAYER_LEVELS[player_object["level"]]["exp"] <= new_exp:
        new_level = player_object["level"] + 1
        new_exp -= PLAYER_LEVELS[player_object["level"]]["exp"]
        await update_player_inventory(player_object["name"], PLAYER_LEVELS[player_object["level"]]["rewards"], player_collection)
    player_collection.update_one({"name": player_object["name"]}, {
        "$set": {
            "level": new_level,
            "experience": new_exp
        }
    })


@player_router.get("/{name}/nearby", status_code=200, response_model=List)
async def get_nearby_players(name: str, request: Request, radius: Optional[int] = 50):
    found = await request.app.state.redis.georadiusbymember("players", name, radius, unit="m")
    found = [x.decode() for x in found]
    found.remove(name)
    return found
