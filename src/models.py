from pydantic import BaseModel, Field


class CoordinatesModel(BaseModel):
    long: float = Field(..., example=-34.6033503396)
    lat: float = Field(..., example=-58.3816562306)