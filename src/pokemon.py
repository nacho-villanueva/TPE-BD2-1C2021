from typing import Dict, List, Optional
import asyncio
import uuid

from fastapi import APIRouter, Request, HTTPException
from pydantic import Field
from pydantic.main import BaseModel

from configurations import *
from utils import generate_nearby_pos

pokemon_router = APIRouter(prefix="/pokemon")

# Each pokemon will leave after 5 hours
POKEMON_EXPIRATION = 60 * 5

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

class CoordinatesModel(BaseModel):
    long: float = Field(..., example=-34.6033503396)
    lat: float = Field(..., example=-58.3816562306)


@pokemon_router.get("/{pokemon_type}", response_model=PokemonModel)
async def get_pokemon_type(pokemon_type: str, request: Request):
    pokemon = await request.app.state.mongodb[MONGODB_DB][MONGODB_POKEMONS_COLLECTION].find_one({'name': pokemon_type})
    if pokemon is not None:
        return pokemon

    raise HTTPException(status_code=404, detail=f"Pokemon {pokemon} not found")

@pokemon_router.put("/spawn_pokemons", response_model=Dict)
async def spawn_pokemon(coords: CoordinatesModel, request: Request):
    pokemons = request.app.state.mongodb[MONGODB_DB][MONGODB_POKEMONS_COLLECTION].aggregate([{ "$sample": { "size": 10 } }])
    
    pokemons_ret = {}
    async for pokemon in pokemons: #100m
        new_coords = generate_nearby_pos(coords.lat, coords.long, 100)
        id = uuid.uuid4()
        coords_str = f"{new_coords[0]},{new_coords[1]}"
        pokemons_ret[id] = {coords_str:pokemon['name']}
        await asyncio.wait([
            request.app.state.redis.geoadd("pokemons", new_coords[0], new_coords[1], "{id}:{pokemon['name']}"),
            request.app.state.redis.setex(f"pokemons:{pokemon['name']}:expire", POKEMON_EXPIRATION, "EXPIRE")            
        ])    

    if not pokemons_ret:
        raise HTTPException(status_code=404, detail=f"Pokemons not found")
    
    return pokemons_ret

async def get_nearby_pokemons():
    pass
