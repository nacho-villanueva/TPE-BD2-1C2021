import math
import random

from .level_info import CHARACTER_LEVELS
from src import utils

NAMES_FILE = "src/names.txt"
LEVELS_INFO_FILE = "level_info.txt"

MAX_LEVEL = 40
MAX_POKEMON_CAPTURED = 300

POWER_UP_COEFFICIENT = 1.025

nf = open(NAMES_FILE)
names = nf.readline().split(",")
names_i = 0
names_j = len(names) - 1
offset = 0


def get_random_name():
    global names_i, names_j, offset
    n = names[(names_i + offset) % len(names)] + "_" + names[(names_j - offset) % len(names)] + str(names_i)
    names_i += 1
    names_j -= 1
    if names_i >= len(names):
        names_i = 0
        names_j = len(names) - 1
        offset += 1

    return n


def get_level_info(level):
    rewards = {}
    for i in range(level):
        for r in CHARACTER_LEVELS[i]["rewards"]:
            current_amount = 0
            if r["item"] in rewards:
                current_amount = rewards[r["item"]]
            rewards[r["item"]] = current_amount + r["amount"]
    if level == MAX_LEVEL:
        xp_for_next_level = 0
    else:
        xp_for_next_level = CHARACTER_LEVELS[level]["exp"]
    return xp_for_next_level, rewards


def randomize_inventory_item(amount):
    if amount < 2:
        return amount
    return round(amount + random.uniform(-amount / 2, amount / 2))


def randomize_team_size(level):
    if level <= 3:
        return round(random.uniform(1, 5))
    mean = (level / MAX_LEVEL) * MAX_POKEMON_CAPTURED
    std = mean / 3
    amount = round(random.normalvariate(mean, std))
    amount = max(0, amount)
    amount = min(MAX_POKEMON_CAPTURED, amount)
    return amount


def randomize_pokemon_caught(level):
    return round((math.exp(level / 3) * 0.2 + 15 * level) * random.uniform(0.9, 1.1))


def get_random_pokemon_type(collection):
    return list(collection.aggregate([{"$sample": {"size": 1}}]))[0]


def get_random_pokemons_types_list(collection, amount):
    return list(collection.aggregate([{"$sample": {"size": amount}}]))


def generate_random_pokemon(player_level, pokemons_collection, pokemon_type):
    level = int(max(min(random.normalvariate(player_level * 0.3, 2), max(player_level - 5, 0)), 0))

    random_coefficient = random.uniform(0.75, 1.25)
    initial_cp = random.uniform(pokemon_type["cp"]["min"], pokemon_type["cp"]["max"])
    cp = round(initial_cp * (POWER_UP_COEFFICIENT ** level))

    poke = {
        "name": pokemon_type["name"],
        "pokemon_type": pokemon_type["name"],
        "level": level,
        "sex": random.choice(["MALE", "FEMALE"]),
        "weight": pokemon_type["weight"] * random_coefficient,
        "height": pokemon_type["height"] * random_coefficient,
        "health": round(random.uniform(pokemon_type["health"]["min"], pokemon_type["health"]["max"])),
        "cp": cp,
        "capture_timestamp": utils.random_datetime(min_year=2016)
    }
    return poke


def generate_random_pokemon_team(player_level, pokemon_amount, pokemons_collection):
    team = []

    pokemon_type = get_random_pokemons_types_list(pokemons_collection, pokemon_amount)

    for p_type in pokemon_type:
        p = generate_random_pokemon(player_level, pokemons_collection, p_type)
        team.append(p)
    return team


def generate_player(pokemons_collection):
    level = round(min(max(random.normalvariate(20, 10), 1), MAX_LEVEL))
    exp_needed, rewards = get_level_info(level)
    pokemon_team_size = randomize_team_size(level)

    inventory = []
    for r in rewards:
        amount = randomize_inventory_item(rewards[r])
        inventory.append({"item": r, "amount": amount})

    player = {
        "name": get_random_name(),
        "level": level,
        "experience": exp_needed - round(random.uniform(0, exp_needed - 5)),
        "stardust": round(level * level * 100 * random.uniform(0.5, 1.1)),
        "total_caught": randomize_pokemon_caught(level),
        "walked_distance": round(random.normalvariate(1, 0.1) * 100 * level),
        "inventory": inventory,
        "pokemons": generate_random_pokemon_team(level, pokemon_team_size, pokemons_collection)
    }
    return player


def populate_players(players_collection, pokemons_collection, player_count=100):
    players = []
    for i in range(player_count):
        players.append(generate_player(pokemons_collection))
    players_collection.insert_many(players)