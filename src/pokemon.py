import asyncio
import random
import time
from datetime import datetime
from typing import List, Optional, Dict
import uuid

from aioredis import Redis
from fastapi import APIRouter, Request, HTTPException, status
from pydantic import Field
from pydantic.main import BaseModel

from src.models import PokemonModel
from src.player import update_player_exp, renew_player_expiration
from src.models import CoordinatesModel
from src.configurations import *
from src.utils import generate_nearby_pos, get_distance

pokemon_router = APIRouter(prefix="/pokemon", tags=["Pokemon Requests"])

# Spawn radius from players in meters
SPAWN_RADIUS = 100

# Distance you can catch a pokemon in meters
CATCH_DISTANCE = 10


class CatchModel(BaseModel):
    pokemon_id: str = Field(..., example="Pikachu:8e97f796-d67e-47ff-b1f8-556416439eec")
    player_name: str = Field(..., example="Ash_Ketchum01")
    pokemon_name: Optional[str] = Field(..., example="Pikachuchis")


@pokemon_router.get("/type", response_model=PokemonModel)
async def get_pokemon_type(pokemon_type: str, request: Request):
    pokemon = await request.app.state.mongodb[MONGODB_DB][MONGODB_POKEMONS_COLLECTION].find_one({'name': pokemon_type})
    if pokemon is not None:
        return pokemon

    raise HTTPException(status_code=404, detail=f"Pokemon {pokemon} not found")


@pokemon_router.put("/spawn_pokemons", response_model=List)
async def spawn_pokemons(coords: CoordinatesModel, request: Request, sample_size: Optional[int] = 10):
    pokemons = request.app.state.mongodb[MONGODB_DB][MONGODB_POKEMONS_COLLECTION].aggregate([{"$sample": {"size": 10}}])

    pokemons_ret = []
    async for pokemon in pokemons:
        new_coords = generate_nearby_pos(coords.lat, coords.long, POKEMON_SPAWN_RADIUS)
        pokemon_id = f"{pokemon['name']}:{uuid.uuid4()}"
        pokemons_ret.append({
            "id": pokemon_id,
            "type": pokemon["name"],
            "coordinates": CoordinatesModel(lat=new_coords[0], long=new_coords[1])
        })
        await asyncio.wait([
            request.app.state.redis.geoadd("pokemons", new_coords[0], new_coords[1], pokemon_id),
            request.app.state.redis.setex(f"pokemons:{pokemon['name']}:expire", random.randint(POKEMON_EXPIRATION_MIN, POKEMON_EXPIRATION_MAX), "EXPIRE")
        ])
    return pokemons_ret


@pokemon_router.get("/nearby", status_code=status.HTTP_200_OK, response_model=List)
async def get_nearby_pokemons(player_name: str, request: Request, radius: Optional[int] = 20):
    pos = await request.app.state.redis.geopos("players", player_name)
    if pos[0] is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Player {player_name} not found")
    found = await request.app.state.redis.georadius("pokemons", pos[0][0], pos[0][1], radius, unit="m")
    return found


@pokemon_router.get("/position", status_code=status.HTTP_200_OK, response_model=CoordinatesModel)
async def get_pokemon_position(pokemon_id: str, request: Request):
    pos = await request.app.state.redis.geopos("pokemons", pokemon_id)
    if pos[0] is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Pokemon {pokemon_id} not found")
    return CoordinatesModel(lat=pos[0][0], long=pos[0][1])


async def generate_pokemon(pokemon_type, state, name=None):
    collection = state.mongodb[MONGODB_DB][MONGODB_POKEMONS_COLLECTION]
    pokemon = await collection.find_one({"name": pokemon_type})

    if pokemon is None:
        return None

    random_coefficient = random.uniform(0.75, 1.25)

    if name is None:
        name = pokemon["name"]

    poke = {
        "name": name,
        "pokemon_type": pokemon["name"],
        "level": 1,
        "sex": random.choice(["MALE", "FEMALE"]),
        "weight": pokemon["weight"] * random_coefficient,
        "height": pokemon["height"] * random_coefficient,
        "health": round(random.uniform(pokemon["health"]["min"], pokemon["health"]["max"])),
        "cp": random.uniform(pokemon["cp"]["min"], pokemon["cp"]["max"]),
        "capture_timestamp": datetime.now()
    }

    return poke


def remove_pokemon(pokemon: str, state, remove_expire=True):
    state.redis.decr("count:pokemons")
    asyncio.ensure_future(state.redis.zrem("pokemons", pokemon))
    if remove_expire:
        asyncio.ensure_future(state.redis.delete(f"pokemons:{pokemon}"))


@pokemon_router.post("/catch", status_code=status.HTTP_200_OK)
async def catch_pokemon(body: CatchModel, request: Request):
    pokemon_pos = await request.app.state.redis.geopos("pokemons", body.pokemon_id)
    player_pos = await request.app.state.redis.geopos("players", body.player_name)

    if len(pokemon_pos) != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Pokemon {body.pokemon_id} not found")
    if len(player_pos) != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Player {body.player_name} not found")

    dist = get_distance(pokemon_pos[0][1], pokemon_pos[0][0], player_pos[0][1], player_pos[0][0])
    if dist > CATCH_DISTANCE:
        raise HTTPException(status_code=status.HTTP_202_ACCEPTED, detail=f"Pokemon {body.pokemon_id} is out of range")

    player_collection = request.app.state.mongodb[MONGODB_DB][MONGODB_PLAYERS_COLLECTION]
    player_object = await player_collection.find_one({'name': body.player_name})
    if len(player_object["pokemons"]) >= MAX_POKEMON_CAPTURED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Team is full")

    [pokemon_type, pokemon_id] = body.pokemon_id.split(":")
    new_pokemon = await generate_pokemon(pokemon_type, request.app.state, name=body.pokemon_name)
    if new_pokemon is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Pokemon type {pokemon_type} not found in database")
    remove_pokemon(body.pokemon_id, request.app.state)

    # Manage Player EXP
    asyncio.ensure_future(update_player_exp(player_object, random.randint(100, 2500), request.app.state))
    renew_player_expiration(body.player_name, request.app.state)

    # Push new pokemon to player's team & increment stardust
    player_collection.update_one({"name": body.player_name},
                                 {
                                     "$push": {"pokemons": new_pokemon},
                                     "$inc": {"stardust": round(random.randint(100, 2500)),
                                              "total_caught": 1}
                                 })


async def pokemon_expiration(pokemon_type, pokemon_id, state):
    print(f"Pokemon Expired: {pokemon_type}:{pokemon_id}")
    remove_pokemon(pokemon_type + ":" + pokemon_id, state, remove_expire=False)