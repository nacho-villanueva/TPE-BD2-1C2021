import requests
from lxml import html

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
        text = attr_elem[0].text
        return text.replace("\n", "").replace("\t", "")
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
        if "Nidoran" in elem.get("href"):
            continue
        if elem.get("href") not in pokemons:
            pokemons.append(elem.get("href"))
    return pokemons


def populate_pokemons_collection(pokemons_collection, bar=None):
    pokemon_list = get_list_of_pokemon()
    all_pokemons = []

    names_i = 0
    i = 0

    if bar is not None:
        bar.maxval = len(pokemon_list)

    for p in pokemon_list:
        info = get_info_from_wikia(p)

        i += 1
        if bar is not None:
            bar.update(i)

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
        except ValueError:
            continue
        if names_i >= 64:
            pokemons_collection.insert_many(all_pokemons)
            all_pokemons = []
            names_i = 0


    if all_pokemons:
        pokemons_collection.insert_many(all_pokemons)
