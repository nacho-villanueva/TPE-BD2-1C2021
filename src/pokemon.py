from typing import List, Optional
import asyncio
import uuid

from fastapi import APIRouter, Request, HTTPException
from pydantic.main import BaseModel
from player import CoordinatesModel

from src.configurations import *
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


@pokemon_router.get("/{pokemon_type}", response_model=PokemonModel)
async def get_pokemon_type(pokemon_type: str, request: Request):
    pokemon = await request.app.state.mongodb[MONGODB_DB][MONGODB_POKEMONS_COLLECTION].find_one({'name': pokemon_type})
    if pokemon is not None:
        return pokemon

    raise HTTPException(status_code=404, detail=f"Pokemon {pokemon} not found")

@pokemon_router.post("/spawn_pokemons", response_model=List[PokemonModel])
async def spawn_pokemon(pokemon_type: str, coords: CoordinatesModel, request: Request):
    pokemons = await request.app.state.mongodb[MONGODB_DB][MONGODB_POKEMONS_COLLECTION].aggregate([{ "$sample": { "size": 10 } }])
    
    if len(pokemons) > 0:
        for pokemon in pokemons: #100m
            new_coords = generate_nearby_pos(coords.lat, coords.long, 100)
            await asyncio.wait([
                request.app.state.redis.geoadd("pokemons", new_coords.lat, new_coords.long, "{uuid.uuid4()}:{pokemon.name}"),
                request.app.state.redis.setex(f"pokemons:{pokemon.name}:expire", POKEMON_EXPIRATION, "EXPIRE")            
            ])    
        return pokemons        

    raise HTTPException(status_code=404, detail=f"Pokemons not found")
    
async def get_nearby_pokemons():
    pass
