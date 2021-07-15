import requests
from lxml import html

from MongoClient import *

WIKI_URL = "https://pokemongo.fandom.com/"

X_PATHS = {
    "name": "//*[@id='firstHeading']",
    "number": "//h3[text()='Number']/following-sibling::div/a",
    "main_type": "//aside/section[1]/section/section[2]/div[1]/div/a[2]",
    "second_type": "//aside/section[1]/section/section[2]/div[2]/div/a[2]",
    "region": "//aside/section[1]/div/div/a",
    "cp_range": "//aside/section[5]/table/tbody/tr/td[1]",
    "health_range": "//aside/section[5]/table/tbody/tr/td[2]",
    "height": "//aside/section[2]/section/section[2]/div[1]",
    "weight": "//aside/section[2]/section/section[2]/div[2]"
}


def get_attribute(tree, attr):
    attr_elem = tree.xpath(X_PATHS[attr])
    if len(attr_elem) > 0:
        return attr_elem[0].text
    else:
        return None


def get_info_from_wikia(url):
    r = requests.get(WIKI_URL + url)
    tree = html.fromstring(r.content)
    stat = {}
    for a in X_PATHS.keys():
        stat[a] = get_attribute(tree, a)
    return stat


def get_list_of_pokemon():
    r = requests.get(WIKI_URL + "List_of_Pokémon")
    tree = html.fromstring(r.content)
    pokemons = []
    all_pokemon_elem = tree.xpath("//div[@class='pogo-list-item-name']/a")
    for elem in all_pokemon_elem:
        pokemons.append(elem.get("href"))
    return pokemons

def populate_pokemons_collection(pokemons_collection):

    pokemon_list = get_list_of_pokemon()
    all_pokemons = []

    names_i = 0

    for p in pokemon_list[752:]:
        info = get_info_from_wikia(p)

        try:
            cp = info["cp_range"].replace(" ", "").replace(",", "").split("-")
            cp = [int(x) for x in cp]
            health = info["health_range"].replace(" ", "").replace(",", "").split("-")
            health = [int(x) for x in health]

            pokemon = {
                "name": info["name"],
                "number": int(info["number"]),
                "main_type": info["main_type"],
                "second_type": info["second_type"],
                "region": info["region"],
                "cp": {
                    "min": cp[0],
                    "max": cp[1]
                },
                "health": {
                    "min": health[0],
                    "max": health[1]
                },
                "height": float(info["height"].replace(" ", "").replace("m", "")),
                "weight": float(info["weight"].replace(" ", "").replace("kg", ""))
            }
            all_pokemons.append(pokemon)
            names_i += 1
            print(pokemon["name"])
        except ValueError:
            continue
        if names_i >= 16:
            pokemons_collection.insert_many(all_pokemons)
            all_pokemons = []
            names_i = 0

    if all_pokemons:
        pokemons_collection.insert_many(all_pokemons)

# populate_pokemons_collection(get_pokemons_collection()) TODO: ADD TO API/CLIENT
