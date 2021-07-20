MONGODB_URI = "mongodb://localhost:27017/"
MONGODB_DB = "pokemongo"
MONGODB_POKEMONS_COLLECTION = "pokemons"
MONGODB_PLAYERS_COLLECTION = "players"

REDIS_URI = "redis://localhost"

MAX_POKEMON_CAPTURED = 300
MAX_LEVEL = 40
POWER_UP_COEFFICIENT = 1.025

# Pokemon disappear after
# Min = 120s = 2min
POKEMON_EXPIRATION_MIN = 120
# Max = 180s = 3min
POKEMON_EXPIRATION_MAX = 180

# Pokemon spawn after
POKEMON_SPAWN_TIME_MIN = 140
POKEMON_SPAWN_TIME_MAX = 200
# Amount of pokemon spawned per logged in players
POKEMON_SPAWN_TIME_MULTIPLIER = 2
POKEMON_SPAWN_RADIUS = 50

# Player Session Expiration Time:  1hr
PLAYER_EXPIRATION = 60 * 60
