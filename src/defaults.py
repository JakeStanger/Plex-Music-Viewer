from json import dumps

import helper

default_settings = {
    "backends": {
        "plex": {
            "enable": False,
            "server_address": "http://localhost:32400",
            "server_token": "",
            "music_library_section": "Music",
            "movies_library_section": "Movies",
            "tv_library_section": "Television",
            "search_results": {
                "music": {
                    "artist": 10,
                    "album": 10,
                    "track": 20
                }
            }
        },
        "mpd": {
            "enable": False,
            "hostname": "localhost",
            "port": 6600
        }
    },
    "music_library": "",  # TODO Make sure this always ends in a /
    "database": "sqlite:///etc/pmv/pmv.db",
    "genius_api": "",
    "colors": {
        "text_dark": "#111111",
        "text_light": "#ffffff"
    },
    "default_permissions": {
        "music": {
            "delete": False,
            "transcode": False,
            "upload": False,
            "edit": False,
            "download": False,
            "view": True
        },
        "movies": {
            "delete": False,
            "transcode": False,
            "upload": False,
            "edit": False,
            "download": False,
            "view": True
        },
        "tv": {
            "delete": False,
            "transcode": False,
            "upload": False,
            "edit": False,
            "download": False,
            "view": True
        }
    },
    "lastfm_key": "",
    "album_art_fetchers": ['plex', 'musicbrainz', 'lastfm', 'local'],
    "log_level": "INFO",
    "secret_key": helper.generate_secret_key()
}


def set_missing_as_default(settings: dict):
    for setting in default_settings:
        if setting not in settings:
            settings[setting] = default_settings[setting]

    write_settings(settings)


def write_settings(settings: dict):
    with open('/etc/pmv/settings.json', 'w') as f:
        f.write(dumps(settings, indent=2))
