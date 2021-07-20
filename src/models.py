from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CoordinatesModel(BaseModel):
    long: float = Field(..., example=-34.6033503396)
    lat: float = Field(..., example=-58.3816562306)


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