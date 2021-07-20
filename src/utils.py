import random
import numpy as np
from datetime import datetime, timedelta
from math import radians, sin, atan2, sqrt, cos


def random_datetime(min_year=1900, max_year=datetime.now().year):
    # generate a datetime in format yyyy-mm-dd hh:mm:ss.000000
    start = datetime(min_year, 1, 1, 00, 00, 00)
    years = max_year - min_year + 1
    end = start + timedelta(days=365 * years)
    return start + (end - start) * random.random()


def get_distance(lat_a, lon_a, lat_b, lon_b):
    R = 6373.0

    lat1 = radians(lat_a)
    lon1 = radians(lon_a)
    lat2 = radians(lat_b)
    lon2 = radians(lon_b)

    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = (sin(dlat / 2)) ** 2 + cos(lat1) * cos(lat2) * (sin(dlon / 2)) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def generate_nearby_pos(lat, lon, distance):
    r = distance/ 111300
    u = np.random.uniform(0,1)
    v = np.random.uniform(0,1)
    w = r * np.sqrt(u)
    t = 2 * np.pi * v
    x = w * np.cos(t)
    x1 = x / np.cos(lon)
    y = w * np.sin(t)
    return [lat + float(x1), lon + float(y)]

print(get_distance(-34.480408360711515, -58.50684100026928, -34.47806466991218, -58.50277477154357))

def print_init_title():
    print("""
    PPPPPPPPPPPPPPPPP                   kkkkkkkk                                                                                                    GGGGGGGGGGGGG                 
    P::::::::::::::::P                  k::::::k                                                                                                 GGG::::::::::::G                 
    P::::::PPPPPP:::::P                 k::::::k                                                                                               GG:::::::::::::::G                 
    PP:::::P     P:::::P                k::::::k                                                                                              G:::::GGGGGGGG::::G                 
      P::::P     P:::::P  ooooooooooo    k:::::k    kkkkkkk eeeeeeeeeeee       mmmmmmm    mmmmmmm      ooooooooooo   nnnn  nnnnnnnn          G:::::G       GGGGGG   ooooooooooo   
      P::::P     P:::::Poo:::::::::::oo  k:::::k   k:::::kee::::::::::::ee   mm:::::::m  m:::::::mm  oo:::::::::::oo n:::nn::::::::nn       G:::::G               oo:::::::::::oo 
      P::::PPPPPP:::::Po:::::::::::::::o k:::::k  k:::::ke::::::eeeee:::::eem::::::::::mm::::::::::mo:::::::::::::::on::::::::::::::nn      G:::::G              o:::::::::::::::o
      P:::::::::::::PP o:::::ooooo:::::o k:::::k k:::::ke::::::e     e:::::em::::::::::::::::::::::mo:::::ooooo:::::onn:::::::::::::::n     G:::::G    GGGGGGGGGGo:::::ooooo:::::o
      P::::PPPPPPPPP   o::::o     o::::o k::::::k:::::k e:::::::eeeee::::::em:::::mmm::::::mmm:::::mo::::o     o::::o  n:::::nnnn:::::n     G:::::G    G::::::::Go::::o     o::::o
      P::::P           o::::o     o::::o k:::::::::::k  e:::::::::::::::::e m::::m   m::::m   m::::mo::::o     o::::o  n::::n    n::::n     G:::::G    GGGGG::::Go::::o     o::::o
      P::::P           o::::o     o::::o k:::::::::::k  e::::::eeeeeeeeeee  m::::m   m::::m   m::::mo::::o     o::::o  n::::n    n::::n     G:::::G        G::::Go::::o     o::::o
      P::::P           o::::o     o::::o k::::::k:::::k e:::::::e           m::::m   m::::m   m::::mo::::o     o::::o  n::::n    n::::n      G:::::G       G::::Go::::o     o::::o
    PP::::::PP         o:::::ooooo:::::ok::::::k k:::::ke::::::::e          m::::m   m::::m   m::::mo:::::ooooo:::::o  n::::n    n::::n       G:::::GGGGGGGG::::Go:::::ooooo:::::o
    P::::::::P         o:::::::::::::::ok::::::k  k:::::ke::::::::eeeeeeee  m::::m   m::::m   m::::mo:::::::::::::::o  n::::n    n::::n        GG:::::::::::::::Go:::::::::::::::o
    P::::::::P          oo:::::::::::oo k::::::k   k:::::kee:::::::::::::e  m::::m   m::::m   m::::m oo:::::::::::oo   n::::n    n::::n          GGG::::::GGG:::G oo:::::::::::oo 
    PPPPPPPPPP            ooooooooooo   kkkkkkkk    kkkkkkk eeeeeeeeeeeeee  mmmmmm   mmmmmm   mmmmmm   ooooooooooo     nnnnnn    nnnnnn             GGGGGG   GGGG   ooooooooooo""")

    print("""
    \t\t\t\t  _____   ___   ___     ___                               _           ___           _                  ___   ___ 
    \t\t\t\t |_   _| | _ \ | __|   | _ )  __ _   ___  ___   ___    __| |  ___    |   \   __ _  | |_   ___   ___   |_ _| |_ _|
    \t\t\t\t   | |   |  _/ | _|    | _ \ / _` | (_-< / -_) (_-<   / _` | / -_)   | |) | / _` | |  _| / _ \ (_-<    | |   | | 
    \t\t\t\t   |_|   |_|   |___|   |___/ \__,_| /__/ \___| /__/   \__,_| \___|   |___/  \__,_|  \__| \___/ /__/   |___| |___|                                                                                                
    """)
