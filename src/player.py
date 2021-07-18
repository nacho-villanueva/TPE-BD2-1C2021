from datetime import datetime

import redis
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import AnyStr

from src.configurations import *
from src.level_info import PLAYER_LEVELS


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
    request.app.state.redis.geoadd("players", coords.lat, coords.long, name)


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


@player_router.post("/{name}/move", status_code=status.HTTP_200_OK, description="Move player to new coordinates.")
async def move_player(name: str, request: Request):
    pass


@player_router.get("/{name}", status_code=status.HTTP_200_OK, response_model=PlayerModel,
                   responses={200: {"model": PlayerModel}, 404: {"detail": AnyStr}})
async def get_player(name: str, request: Request):
    player = await request.app.state.mongodb[MONGODB_DB][MONGODB_PLAYERS_COLLECTION].find_one({'name': name})
    if player is not None:
        return JSONResponse(status_code=status.HTTP_200_OK, content=player)

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Player {name} not found")

def player_session_expiration(msg):
    pass