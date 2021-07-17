from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from fastapi.responses import HTMLResponse

from src.configurations import *


class PlayerModel(BaseModel):
    name: str
    level: int
    experience: int
    stardust: int
    total_caught: int
    walked_distance: int
    inventory: list
    pokemons: list

    def __str__(self):
        return self.name


player_router = APIRouter(prefix="/player")


@player_router.post("/{name}/")
async def login_player(name: str, request: Request):
    pass


async def register_player(name: str, request: Request):
    pass


@player_router.post("/{name}/move")
async def move_player(name: str, request: Request):
    pass


@player_router.get("/{name}", response_model=PlayerModel)
async def get_player(name: str, request: Request):
    player = await request.app.state.mongodb[MONGODB_DB][MONGODB_PLAYERS_COLLECTION].find_one({'name': name})
    if player is not None:
        return player

    raise HTTPException(status_code=404, detail=f"Player {name} not found")
