# app-from-connect-to-api-migration

Used to migrate client data from connect database to api database after applying api migration [#0001_initial.py](https://github.com/bimdata/python-api/blob/feature/marketplace/app/migrations/0001_initial.py)

# How use it

First, install the dependencies:

```
pip install -r requirement.txt
```

Then, there are two parts:

The first is to retrieve a compressed json containing the apps contained in the connect database.
For this, the `dump_apps.py` script interacts with two docker containers named 'connect' and 'api'.

```
python dump_apps.py
```

In output, the file is located here: `/var/tmp/dumpdata.keycloak.tar`


The second one restores the apps in the api database using this same file:

```
python restore_apps.py
```

This second step is automated in [quick-start on premise](https://github.com/bimdata/quickstart-onpremise)
