import requests
from lxml import html
import pymongo

WIKI_URL = "https://pokemongo.fandom.com/"

# X_PATHS = {
#     "number": "//aside/section[2]/div[1]/div/a",
#     "main_type": "//aside/section[1]/section/section[2]/div[1]/div/a[2]",
#     "second_type": "//aside/section[1]/section/section[2]/div[2]/div/a[2]",
#     "region": "//aside/section[1]/div/div/a",
#     "cp_range": "//aside/section[5]/table/tbody/tr/td[1]",
#     "health_range": "//aside/section[5]/table/tbody/tr/td[2]",
#     "height_range_xs": "//aside/section[8]/div[1]/div",
#     "height_range_normal": "//aside/section[8]/div[2]/div",
#     "height_range_xl": "//aside/section[8]/div[3]/div",
#     "weight_range_xs": "//aside/section[9]/div[1]/div",
#     "weight_range_normal": "//aside/section[9]/div[2]/div",
#     "weight_range_xl": "//aside/section[9]/div[3]/div"
# }

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


client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["pokemongo"]
collection = db["pokemons"]

pokemon_list = get_list_of_pokemon()
all_pokemons = []

i = 0

# print(len(pokemon_list))

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
        i += 1
    except ValueError:
        continue
    if i >= 16:
        print([x["name"] for x in all_pokemons])
        collection.insert_many(all_pokemons)
        all_pokemons = []
        i = 0

if all_pokemons:
    print([x["name"] for x in all_pokemons])
    collection.insert_many(all_pokemons)
