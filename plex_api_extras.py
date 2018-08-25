from json import dumps, loads
from typing import Optional

import requests
import xmltodict

REQUEST_DATA = "?checkFiles=1&includeExtras=1&X-Plex-Token="


def _get_bitrate(metadata: dict) -> Optional[str]:
    """
    :param metadata: The track XML metadata
    :return: The track bitrate
    """
    try:
        return str(metadata['Stream']['@bitrate'])
    except KeyError:
        try:
            return str(metadata['Stream'][0]['@bitrate'])
        except KeyError:
            return None


def _get_codec(metadata: dict) -> str:
    """
    :param metadata: The track XML metadata
    :return: The track codec
    """
    try:
        return str(metadata['Stream']['@codec'])
    except KeyError:
        return str(metadata['Stream'][0]['@codec'])


def _get_size(metadata: dict) -> str:
    """
    :param metadata: The track XML metadata
    :return: The track size_formatted in bytes
    """
    return metadata['@size']


def _get_download_location(metadata: dict, path: str) -> str:
    """
    :param metadata: The track XML metadata
    :param path: The path to the music library root
    :return: The relative track download path
    """
    base_location = metadata['@file']
    return base_location.replace(path, "music")


def get_additional_track_data(track_key, settings):
    """
    Fetches the track bitrate, codec, size_formatted,
    and download location from XML.
    :param track_key: The track library key
    :param settings: The global settings dictionary
    :return: A dictionary of extra data
    """
    url = settings['serverAddress'] + track_key + REQUEST_DATA + settings['serverToken']
    r = requests.get(url)

    metadata = loads(dumps(xmltodict.parse(r.text)))['MediaContainer']['Track']['Media']['Part']

    return {'bitrate': _get_bitrate(metadata), 'codec': _get_codec(metadata), 'size': int(_get_size(metadata)),
            'downloadURL': _get_download_location(metadata, settings['musicLibrary'])}


def get_download_location_post(track_key, settings):
    """
    Used to avoid fetching all extra metadata
    when just the download location is wanted.
    Named such as it usually used in POST requests.
    :param track_key: The track library key
    :param settings: The global settings dictionary
    :return:The relative track download path.
    """
    url = settings['serverAddress'] + track_key + REQUEST_DATA + settings['serverToken']
    r = requests.get(url)

    system_path = loads(dumps(xmltodict.parse(r.text)))['MediaContainer']['Track']['Media']['Part']['@file']
    return system_path.replace(settings['musicLibrary'], "music")


def get_torrent_location(album_key, settings):
    """
    :param album_key: The library album key
    :param settings: The global settings dictionary
    :return: The location of the album's torrent
    """
    url = settings['serverAddress'] + album_key + REQUEST_DATA + settings['serverToken']
    r = requests.get(url)

    system_path = loads(dumps(xmltodict.parse(r.text)))['MediaContainer']['Track']['Media']['Part']['@file']
    return system_path.replace(settings['musicLibrary'], "torrents").rsplit(".", 1)[0] + ".torrent".encode('utf-8')