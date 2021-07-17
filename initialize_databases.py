from pymongo import MongoClient

from src.configurations import *
from src.populate_players import populate_players
from src.populate_pokemons import populate_pokemons_collection

import progressbar

print("Initializing MongoDB\n")

cli = MongoClient(MONGODB_URI)
pokemon_c = cli[MONGODB_DB][MONGODB_POKEMONS_COLLECTION]
player_c = cli[MONGODB_DB][MONGODB_PLAYERS_COLLECTION]

pokemon_c.create_index([('name', 1)], unique=True)
player_c.create_index([('name', 1)], unique=True)

print("Populating Pokemon...")
pokemon_bar = progressbar.ProgressBar(widgets=[progressbar.SimpleProgress(), "\t-\t", progressbar.AdaptiveETA()]).start()
populate_pokemons_collection(pokemon_c, bar=pokemon_bar)
pokemon_bar.finish()
print("Done.\n")

print("Populating Players...")
populate_players(player_c, pokemon_c)
print("Done\n")
