import asyncio
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.configurations import *
from src.level_info import PLAYER_LEVELS
from src.utils import get_distance

# Player will logout after 1 hour = 60 * 60 seconds
PLAYER_EXPIRATION = 60


class Message(BaseModel):
    message: str


class PlayerModel(BaseModel):
    name: str = Field(..., example="Ash_Ketchum")
    level: int = Field(..., example=39)
    experience: int = Field(..., example=883025)
    stardust: int = Field(..., example=91879)
    total_caught: int = Field(..., example=2350)
    walked_distance: int = Field(..., example=2350)
    inventory: list = Field(..., example=[{"item": "Poke Ball", "amount": 269}, {"item": "Potion", "amount": 27}])
    pokemons: list = Field(..., example=[
        {"name": "Pikachu", "pokemon_type": "Pikachu", "level": 4, "sex": "MALE", "weight": 5.34, "height": 0.35,
         "health": 76, "cp": 896, "capture_timestamp": datetime.fromisoformat("2017-06-01T04:00:00.528+00:00")}])

    def __str__(self):
        return self.name


class CoordinatesModel(BaseModel):
    long: float = Field(..., example=-34.6033503396)
    lat: float = Field(..., example=-58.3816562306)


player_router = APIRouter(prefix="/player", tags=["Player Requests"])


@player_router.post("/{name}/")
async def login_player(name: str, coords: CoordinatesModel, request: Request):
    collection = request.app.state.mongodb[MONGODB_DB][MONGODB_PLAYERS_COLLECTION]
    if await collection.find_one({'name': name}) is not None:
        await asyncio.wait([
            request.app.state.redis.geoadd("players", coords.lat, coords.long, name),
            request.app.state.redis.hset(f"players:{name}", "walked_distance", 0),
            request.app.state.redis.setex(f"players:{name}:expire", PLAYER_EXPIRATION, "EXPIRE")
        ])
        return
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {name} not registered")


@player_router.post("/{name}/logout")
async def logout_player(name: str, request: Request):
    await request.app.state.redis.delete(f"players:{name}:expire")
    await player_session_expiration(name, request.app.state)


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
async def move_player(name: str, new_position: CoordinatesModel, request: Request):
    old_pos = await request.app.state.redis.geopos("players", name)
    if len(old_pos) == 1:
        asyncio.ensure_future(request.app.state.redis.geoadd("players", new_position.lat, new_position.long, name))
        asyncio.ensure_future(update_distance(old_pos[0], new_position, name, request.app.state))
        return
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Player {name} not found")


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


async def player_session_expiration(name, state):
    state.redis.zrem("players", name)
    walked = float(await state.redis.hget(f"players:{name}", "walked_distance"))
    if walked > 0:
        update_mongo_distance(name, walked, state)
    await state.redis.delete(f"players:{name}")
