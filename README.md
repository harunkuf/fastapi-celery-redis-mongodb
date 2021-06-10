# fastapi-celery-redis-mongodb
 school library api with fastapi, celery, redis and mongodb

To run this project with a docker image,
after cloning this repo and cd'ing into the repo in your linux terminal, run 
```console
sh local_env_up.sh
``` 
to start the application.

Apllication runs on http://localhost:5000/ and to use the functions in fastapi you have to use http://localhost:5000/docs . Currently all functions are returning their outputs as strings and url input is not possible, you will have to use /docs.

Note: In order to run this application you must change username:password to your username and password from MongoDB website in app/cluster_password.txt and celery/cluster_password.txt

This project does not work with a local MongoDB server. You will need to make adjustments in order to run with  alocal MongoDB server.
