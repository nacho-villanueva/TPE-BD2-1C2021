# Pokemon GO - Data Base II ITBA Project

![Title Image](https://lh3.googleusercontent.com/3TSaKxXGo2wT0lu0AyNUBnkk6wkCC2AzOhJyy3JXIPm-AmZ1k9DSAroWeBUyePswCZSs5lVp3mPF7HzUpY9VPlyOV5eddITONINr3WSqLNLm=e365-w600)

This project consists in an attempt of a reduced replica of the Pokemon GO API, with the objective of showing a possible implementation of how the data bases work. For this the following DBs were uses:
* MongoDB: In charge of mainting all the information of the players and the pokemons
* Redis: In charge of maintainin all the information which was updated in real-time such as players positions, pokemons positions, etc.

FastApi was used in order to create the API.

## Getting Started 🚀

### Dependencies
The project requires of the following to be installed:
* Docker
* Python3 & pip 

### Installing
First you will need to install an instance of Redis and MongoDB. The easiest way to set up this is with Docker using the following commands:
This will retrieve de docker images.
```bash
docker pull redis
docker pull mongo
```
This will run each of the instances. If the DBs instances aren't in localhost or you change the port, be sure to update the server's location in ```src/configurations.py```
```
docker run --name pokemon-redis -p 6379:6379 -d redis
docker run --name pokemon-mongo –p 27017:27017 -d mongo 
```
Now we will need to install the requirements needed for the project. We can do this by running the following pip command in the projects root:
```
pip -r requirements.txt
```

Now that the DBs are running and all the requirements are installed, we need to configure the DBs. For this we only need to run the ```initialize_databases.py``` script which can be found in the projects root folder.

And we are done! Next we will see how to run it.
### Executing Server
In order to run the server locally, we only need to run the following command from the projects root
```
uvicorn src.main:app --host=127.0.0.1 --port=8000
```
This will run the API in ```127.0.0.1:8000```. If uvicorn isn't installed it can easily be installed using```pip install uvicorn```

Once the server is running, you can head to ```127.0.0.1:8000/docs``` where you can find swagger with a list of the posible API requests, and some examples on how to execute them.

## Authors

Ignacio Villanueva - [Webpage](https://ignacio.villanueva.it/) - [LinkedIn](https://www.linkedin.com/in/ignacio-villanueva-256541176) -

Gabriel Silvatici - [LinkedIn](https://www.linkedin.com/in/gabriel-silvatici-dayan-233b87b3/) -
