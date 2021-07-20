import asyncio
import random
from datetime import datetime
from typing import Optional, List
import uuid

from fastapi import APIRouter, Request, HTTPException, status
from pydantic.main import BaseModel
from player import CoordinatesModel

from src.player import update_player_exp
from src.models import CoordinatesModel
from src.configurations import *
from src.utils import generate_nearby_pos, get_distance

pokemon_router = APIRouter(prefix="/pokemon", tags=["Pokemon Requests"])

# Pokemon will disappear after 5min = 5 * 60
POKEMON_EXPIRATION = 5 * 60

# Spawn radius from players in meters
SPAWN_RADIUS = 100

# Distance you can catch a pokemon in meters
CATCH_DISTANCE = 10


class PokemonModel(BaseModel):
    name: str
    number: int
    main_type: str
    second_type: Optional[str]
    region: str
    cp: dict
    health: dict
    height: float
    weight: float


@pokemon_router.get("/{pokemon_type}", response_model=PokemonModel)
async def get_pokemon_type(pokemon_type: str, request: Request):
    pokemon = await request.app.state.mongodb[MONGODB_DB][MONGODB_POKEMONS_COLLECTION].find_one({'name': pokemon_type})
    if pokemon is not None:
        return pokemon

    raise HTTPException(status_code=404, detail=f"Pokemon {pokemon} not found")


@pokemon_router.post("/spawn_pokemons", response_model=List[PokemonModel])
async def spawn_pokemon(pokemon_type: str, coords: CoordinatesModel, request: Request):
    pokemons = await request.app.state.mongodb[MONGODB_DB][MONGODB_POKEMONS_COLLECTION].aggregate(
        [{"$sample": {"size": 10}}])

    if len(pokemons) > 0:
        for pokemon in pokemons:  # 100m
            new_coords = generate_nearby_pos(coords.lat, coords.long, 100)
            await asyncio.wait([
                request.app.state.redis.geoadd("pokemons", new_coords.lat, new_coords.long, "{uuid.uuid4()}:{pokemon.name}"),
                request.app.state.redis.setex(f"pokemons:{pokemon.name}:expire", POKEMON_EXPIRATION, "EXPIRE")            
            ])    
        return pokemons        

    raise HTTPException(status_code=404, detail=f"Pokemons not found")


async def get_nearby_pokemons():
    pass


async def pokemon_spawner(state):
    pass


async def generate_pokemon(pokemon_type, state):
    collection = state.mongodb[MONGODB_DB][MONGODB_POKEMONS_COLLECTION]
    pokemon = await collection.find_one({"name": pokemon_type})

    if pokemon is None:
        return None

    random_coefficient = random.uniform(0.75, 1.25)

    poke = {
        "name": pokemon["name"],
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


@pokemon_router.post("/{pokemon}/catch", status_code=status.HTTP_200_OK)
async def catch_pokemon(pokemon: str, player: str, request: Request):
    await asyncio.wait([
        pokemon_pos := request.app.state.redis.geopos("pokemons", pokemon),
        player_pos := request.app.state.redis.geopos("players", player)
    ])

    if len(pokemon_pos) != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Pokemon {pokemon} not found")
    if len(player_pos) != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Player {player} not found")

    dist = get_distance(pokemon_pos[0][1], pokemon_pos[0][0], player_pos[0][1], player_pos[0][0])
    if dist > CATCH_DISTANCE:
        raise HTTPException(status_code=status.HTTP_202_ACCEPTED, detail=f"Pokemon {pokemon} is out of range")

    player_collection = request.app.state.mongodb[MONGODB_DB][MONGODB_PLAYERS_COLLECTION]
    player = player_collection.find_one({"name", player})
    if len(player["pokemons"]) >= MAX_POKEMON_CAPTURED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Team is full")

    [pokemon_type, pokemon_id] = pokemon.split(":")
    new_pokemon = await generate_pokemon(pokemon_type, request.app.state)
    if new_pokemon is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Pokemon type {pokemon_type} not found in database")
    # Manage Player EXP
    asyncio.ensure_future(update_player_exp(player, random.randint(100, 2500), request.app.state))

    # Push new pokemon to player's team & increment stardust
    player_collection.update({"name", player},
                             {
                                 "$push": {"pokemons"},
                                 "$inc": {"stardust", round(random.randint(100, 2500))}
                             })
