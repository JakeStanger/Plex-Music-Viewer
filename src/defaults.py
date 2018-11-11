from json import dumps

import helper

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
    "music_library": "",  # TODO Make sure this always ends in a /
    "database": "mysql://user:password@localhost:3306/MyDatabase",
    "secret_key": helper.generate_secret_key(),
    "genius_api": "",
    "colors": {
        "textDark": "#111111",
        "textLight": "#ffffff"
    },
    "newUserPerms": [0, 0, 0],
    "lastfm_key": "",
    "album_art_fetchers": ['plex', 'musicbrainz', 'lastfm', 'local'],
    "log_level": "INFO"
}


def set_missing_as_default(settings: dict):
    for setting in default_settings:
        if setting not in settings:
            settings[setting] = default_settings[setting]

    write_settings(settings)


def write_settings(settings: dict):
    with open('settings.json', 'w') as f:
        f.write(dumps(settings, indent=2))
