from json import dumps, loads
import requests
import xmltodict

REQUEST_DATA = "?checkFiles=1&includeExtras=1&X-Plex-Token="


def getBitrate(metadata):
    """
    :param metadata: The track XML metadata
    :return: The track bitrate
    """
    try:
        return str(metadata['Stream']['@bitrate'])
    except:
        try:
            return str(metadata['Stream'][0]['@bitrate'])
        except:
            return "---"


def getCodec(metadata):
    """
    :param metadata: The track XML metadata
    :return: The track codec
    """
    try:
        return str(metadata['Stream']['@codec'])
    except:
        return str(metadata['Stream'][0]['@codec'])


def getSize(metadata):
    """
    :param metadata: The track XML metadata
    :return: The track size_formatted in bytes
    """
    return metadata['@size']


def getDownloadLocation(metadata, path):
    """
    :param metadata: The track XML metadata
    :param path: The path to the music library root
    :return: The relative track download path
    """
    baseLocation = metadata['@file']
    return baseLocation.replace(path, "music")


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

    return {'bitrate': getBitrate(metadata), 'codec': getCodec(metadata), 'size': int(getSize(metadata)),
            'downloadURL': getDownloadLocation(metadata, settings['musicLibrary'])}


def getDownloadLocationPOST(trackKey, settings):
    """
    Used to avoid fetching all extra metadata
    when just the download location is wanted.
    Named such as it usually used in POST requests.
    :param trackKey: The track library key
    :param settings: The global settings dictionary
    :return:The relative track download path.
    """
    url = settings['serverAddress'] + trackKey + REQUEST_DATA + settings['serverToken']
    r = requests.get(url)

    systemPath = loads(dumps(xmltodict.parse(r.text)))['MediaContainer']['Track']['Media']['Part']['@file']
    return systemPath.replace(settings['musicLibrary'], "music")


def getTorrentLocation(albumKey, settings):
    """
    :param albumKey: The library album key
    :param settings: The global settings dictionary
    :return: The location of the album's torrent
    """
    url = settings['serverAddress'] + albumKey + REQUEST_DATA + settings['serverToken']
    r = requests.get(url)

    systemPath = loads(dumps(xmltodict.parse(r.text)))['MediaContainer']['Track']['Media']['Part']['@file']
    return systemPath.replace(settings['musicLibrary'], "torrents").rsplit(".", 1)[0] + ".torrent".encode('utf-8')