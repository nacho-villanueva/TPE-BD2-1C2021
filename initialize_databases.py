from src.PopulatePokemons import populate_pokemons_collection

print("Initializing MongoDB")

cli = pymongo.MongoClient(MONGODB_URI)
pokemon_c = cli[MONGODB_DB][MONGODB_POKEMONS_COLLECTION]
player_c = cli[MONGODB_DB][MONGODB_PLAYERS_COLLECTION]

print("Populating Pokemons...")
populate_pokemons_collection()
populate_players(player_c, pokemon_c)

