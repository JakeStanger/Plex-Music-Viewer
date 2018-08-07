default_settings = {
    "librarySection": "Music",
    "serverAddress": "http://localhost:32400",
    "interfaceToken": "",
    "searchResults": {
        "artistResults": 10,
        "albumResults": 10,
        "trackResults": 20
    },
    "serverToken": "",
    "database": {
        "user": "",
        "password": "",
        "database": "",  # TODO Automatically create database and tables if missing
        "hostname": "localhost"
    },
    "secret_key": "",
    "genius_api": "",
    "colors": {
        "textDark": "#111111",
        "textLight": "#ffffff"
    },
    "newUserPerms": [0, 0, 0]
}


def set_defaults():
    pass


def set_missing_as_default():
    pass
