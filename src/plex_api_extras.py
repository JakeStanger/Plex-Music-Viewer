from json import dumps, loads

import requests
import xmltodict

REQUEST_DATA = "?checkFiles=1&includeExtras=1&X-Plex-Token="


def get_additional_track_data(track_key: str):
    print("WARNING! - Using get_additional_track_data, a deprecated function")
    """
    Fetches the track bitrate, codec, size_formatted,
    and download location from XML.
    :param track_key: The track library key
    :param settings: The global settings dictionary
    :return: A dictionary of extra data
    """
    import pmv
    settings = pmv.settings
    url = settings['plex']['server_address'] + track_key + REQUEST_DATA + settings['plex']['server_token']
    r = requests.get(url, headers={'Accept': 'application/json'})
    return r.json()['MediaContainer']['Metadata']


def get_torrent_location(album_key, settings):
    """
    :param album_key: The library album key
    :param settings: The global settings dictionary
    :return: The location of the album's torrent
    """
    url = settings['plex']['server_address'] + album_key + REQUEST_DATA + settings['plex']['server_token']
    r = requests.get(url)
    # TODO Refactor to use JSON instead of XML
    system_path = loads(dumps(xmltodict.parse(r.text)))['MediaContainer']['Track']['Media']['Part']['@file']
    return system_path.replace(settings['musicLibrary'], "torrents").rsplit(".", 1)[0] + ".torrent".encode('utf-8')
