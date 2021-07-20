import asyncio
from typing import Optional, List

from fastapi import APIRouter, Request, status, HTTPException
from pydantic import BaseModel, Field

from .level_info import PLAYER_LEVELS
from .models import CoordinatesModel
from .player import login_player, update_player_inventory
from .configurations import *
from .utils import generate_nearby_pos

demo_router = APIRouter(prefix="/demo", tags=["Demo/Cheats Requests"])


class GiveItemModel(BaseModel):
    player_name: str = Field(..., example="Ash_Ketchum01")
    item: str = Field(..., example="Poke Ball")
    amount: int = Field(..., example=10)


@demo_router.post("/login_randoms", response_model=List)
async def login_random_players(coordinates: CoordinatesModel, request: Request, radius: Optional[float] = 500.0,
                               sample_size: Optional[int] = 20):
    players = request.app.state.mongodb[MONGODB_DB][MONGODB_PLAYERS_COLLECTION].aggregate(
        [{"$sample": {"size": sample_size}}])

    ret = []

    async for p in players:
        ret.append(p["name"])
        coords = generate_nearby_pos(coordinates.lat, coordinates.long, radius)
        asyncio.ensure_future(
            login_player(p, CoordinatesModel(lat=coords[0], long=coords[1]), request.app.state))

    return ret


@demo_router.post("/give_item", status_code=status.HTTP_200_OK)
async def give_player_item(model: GiveItemModel, request: Request):
    player_collection = request.app.state.mongodb[MONGODB_DB][MONGODB_PLAYERS_COLLECTION]
    player_collection.update_one({"name": model.player_name, "inventory.item": model.item},
                                 {"$inc": {"inventory.$.amount": model.amount}})
    return "OK"


@demo_router.post("/level_up_player", status_code=status.HTTP_200_OK)
async def level_up_player(player_name: str, request: Request):
    player_collection = request.app.state.mongodb[MONGODB_DB][MONGODB_PLAYERS_COLLECTION]
    player = await player_collection.find_one_and_update({"name": player_name}, {"$inc": {"level": 1}, "$set": {"experience": 0}})
    if player is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Player {player_name} not found")
    if player["level"] < MAX_LEVEL-1:
        await update_player_inventory(player_name, PLAYER_LEVELS[player["level"]]["rewards"], player_collection)
    return
