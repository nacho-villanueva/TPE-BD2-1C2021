import pymongo

MONGODB_URI = "mongodb://localhost:27017/"
MONGODB_DB = "pokemongo"
MONGODB_POKEMONS_COLLECTION = "pokemons"
MONGODB_PLAYERS_COLLECTION = "players"

__client = None


def __init_client():
    global __client
    if __client is None:
        __client = pymongo.MongoClient(MONGODB_URI)
    return __client


def get_mongo_client():
    global __client
    __init_client()
    return __client


def get_pokemons_collection():
    cli = __init_client()
    return cli[MONGODB_DB][MONGODB_POKEMONS_COLLECTION]


def get_players_collection():
    cli = __init_client()
    return cli[MONGODB_DB][MONGODB_PLAYERS_COLLECTION]
