import asyncio
import random
from datetime import datetime
from typing import List, Optional
import uuid

from fastapi import APIRouter, Request, HTTPException, status

from src.models import PokemonModel
from src.player import update_player_exp
from src.models import CoordinatesModel
from src.configurations import *
from src.utils import generate_nearby_pos, get_distance

pokemon_router = APIRouter(prefix="/pokemon", tags=["Pokemon Requests"])

# Pokemon disappear after
# Min = 120s = 2min
POKEMON_EXPIRATION_MIN = 10
# Max = 180s = 3min
POKEMON_EXPIRATION_MAX = 30



# Spawn radius from players in meters
SPAWN_RADIUS = 100

# Distance you can catch a pokemon in meters
CATCH_DISTANCE = 10


@pokemon_router.get("/{pokemon_type}", response_model=PokemonModel)
async def get_pokemon_type(pokemon_type: str, request: Request):
    pokemon = await request.app.state.mongodb[MONGODB_DB][MONGODB_POKEMONS_COLLECTION].find_one({'name': pokemon_type})
    if pokemon is not None:
        return pokemon

    raise HTTPException(status_code=404, detail=f"Pokemon {pokemon} not found")


@pokemon_router.post("/spawn_pokemons")
async def spawn_pokemon(coords: CoordinatesModel, request: Request):
    pokemons = request.app.state.mongodb[MONGODB_DB][MONGODB_POKEMONS_COLLECTION].aggregate(
        [{"$sample": {"size": 10}}])

    async for pokemon in pokemons:  # 100m
        new_coords = generate_nearby_pos(coords.lat, coords.long, 100)
        pokemon_id = uuid.uuid4()
        await asyncio.wait([
            request.app.state.redis.geoadd("pokemons", new_coords[0], new_coords[1], f"{pokemon['name']}:{pokemon_id}"),
            request.app.state.redis.setex(f"pokemons:{pokemon['name']}:{pokemon_id}:expire", random.randint(POKEMON_EXPIRATION_MIN, POKEMON_EXPIRATION_MAX),
                                          "EXPIRE")
        ])


@pokemon_router.get("/nearby", status_code=status.HTTP_200_OK, response_model=List)
async def get_nearby_pokemons(player_name: str, request: Request):
    pos = await request.app.state.redis.geopos("players", player_name)
    if pos[0] is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Player {player_name} not found")
    found = await request.app.state.redis.georadius("pokemons", pos[0][0], pos[0][1], 20, unit="m")
    return found


async def pokemon_spawner(state):
    pass


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
    asyncio.ensure_future(state.redis.zrem("pokemons", pokemon))
    if remove_expire:
        asyncio.ensure_future(state.redis.delete(f"pokemons:{pokemon}"))


@pokemon_router.post("/catch", status_code=status.HTTP_200_OK)
async def catch_pokemon(pokemon: str, player_name: str, pokemon_name: Optional[str], request: Request):
    pokemon_pos = await request.app.state.redis.geopos("pokemons", pokemon)
    player_pos = await request.app.state.redis.geopos("players", player_name)

    if len(pokemon_pos) != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Pokemon {pokemon} not found")
    if len(player_pos) != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Player {player_name} not found")

    dist = get_distance(pokemon_pos[0][1], pokemon_pos[0][0], player_pos[0][1], player_pos[0][0])
    if dist > CATCH_DISTANCE:
        raise HTTPException(status_code=status.HTTP_202_ACCEPTED, detail=f"Pokemon {pokemon} is out of range")

    player_collection = request.app.state.mongodb[MONGODB_DB][MONGODB_PLAYERS_COLLECTION]
    player_object = await player_collection.find_one({'name': player_name})
    if len(player_object["pokemons"]) >= MAX_POKEMON_CAPTURED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Team is full")

    [pokemon_type, pokemon_id] = pokemon.split(":")
    new_pokemon = await generate_pokemon(pokemon_type, request.app.state, name=pokemon_name)
    if new_pokemon is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Pokemon type {pokemon_type} not found in database")
    # Manage Player EXP
    asyncio.ensure_future(update_player_exp(player_object, random.randint(100, 2500), request.app.state))

    # Push new pokemon to player's team & increment stardust
    player_collection.update_one({"name": player_name},
                                 {
                                     "$push": {"pokemons": new_pokemon},
                                     "$inc": {"stardust": round(random.randint(100, 2500)),
                                              "total_caught": 1}
                                 })


async def pokemon_expiration(pokemon_type, pokemon_id, state):
    print(f"Pokemon Expired: {pokemon_type}:{pokemon_id}")
    remove_pokemon(pokemon_type + ":" + pokemon_id, state, remove_expire=False)
