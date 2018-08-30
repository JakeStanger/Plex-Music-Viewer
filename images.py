import os
import re
from io import BytesIO
from typing import Optional
from urllib.request import urlopen

import musicbrainzngs as mb
import numpy as np
import pylast as pl
import scipy
import scipy.cluster
import scipy.misc
from PIL import Image

import app
import database
from plex_helper import AlbumWrapper


def get_friendly_thumb_id(thumb_id: str) -> str:
    """
    Gets both numerical values in the thumb id
    and separates them with a dash.

    Useful for cases such as file names.

    :param thumb_id: The full thumb-id
    :return: The numerical values separated by a dash.
    """
    return '-'.join(num for num in re.findall('\\d+', thumb_id))


def _get_url_as_bytesio(url: str) -> BytesIO:
    return BytesIO(urlopen(url).read())


def _fetch_from_plex(album: AlbumWrapper) -> Optional[BytesIO]:
    """
    Queries the Plex server using the ID
    and fetches the set thumbnail for the item.
    :param album
    :return:
    """

    # TODO return none if not using plex

    settings = app.settings
    if not settings['serverToken']:
        return None

    thumb_id = '/' + album.thumb
    url = settings['serverAddress'] + thumb_id + "?X-Plex-Token=" + settings['serverToken']

    return _get_url_as_bytesio(url)


def _fetch_from_musicbrainz(album: AlbumWrapper) -> Optional[str]:
    release = mb.search_releases(artist=album.parentTitle, release=album.title, limit=1)['release-list'][0]

    size = 250

    filename = 'images/%s_250.jpg' % get_friendly_thumb_id(album.thumb)

    try:
        with open(filename, 'wb') as f:
            f.write(mb.get_image_front(release['id'], size=size))
    except mb.ResponseError:  # Image not found
        return None

    return filename


def _fetch_from_lastfm(album: AlbumWrapper):
    settings = app.settings
    if not settings['lastfm_key']:
        return None

    network = pl.LastFMNetwork(api_key=app.settings['lastfm_key'])

    album_search = pl.AlbumSearch(album.title, network)

    if album_search.get_total_result_count() == 0:
        return None

    # Get first result
    album = album_search.get_next_page()[0]

    url = album.get_cover_image()
    return _get_url_as_bytesio(url)


def _fetch_from_local(album: AlbumWrapper):
    return None  # TODO write function


def save_image_to_disk(thumb_id: str, image: Image, width: Optional[int]=None):
    """
    Writes the given image to disk using
    its friendly ID as the filename.

    :param thumb_id: The image thumbnail ID
    :param image: The image object
    :param width: The desired width of the image
    :return:
    """
    if not os.path.exists('images'):
        os.makedirs('images')

    image.save("images/%s_%s.png" % (get_friendly_thumb_id(thumb_id), str(width) if width else ''), 'PNG', quality=90)


def read_image_from_disk(thumb_id, width: Optional[int]=None):
    try:
        return Image.open("images/%s_%s.png" % (get_friendly_thumb_id(thumb_id), str(width) if width else ''))
    except FileNotFoundError:
        return None


def get_raw_image(thumb_id: str, width: int=None) -> Image:
    if thumb_id.startswith('/'):
        thumb_id = thumb_id[1:]

    cached = read_image_from_disk(thumb_id, width)
    if cached:
        return cached

    friendly_id = get_friendly_thumb_id(thumb_id)
    album_id = int(friendly_id.split('-')[0])

    album = AlbumWrapper(row=database.get_album_by_key(album_id))

    search_methods = app.settings['album_art_fetchers']
    i = 0
    file = None

    # Call local functions for each fetching method until a result is found
    while not file:
        file = globals()['_fetch_from_%s' % search_methods[i]](album)
        i += 1

    image = Image.open(file)
    # TODO Other thumb fetching techniques (look for image in directory, last.fm, etc...)

    if width:
        size = int(width), int(width)
        image.thumbnail(size, Image.ANTIALIAS)

    save_image_to_disk(thumb_id, image, width)
    return image
    # except Exception as e:
    #     print(e)
    #     app.throw_error(400, "invalid thumb-id")


def get_image(thumb_id: str, width: Optional[int]=None) -> BytesIO:
    image = get_raw_image(thumb_id, width)
    tmp_image = BytesIO()
    image.save(tmp_image, 'PNG', quality=90)
    tmp_image.seek(0)

    return tmp_image


def get_predominant_colour(thumb_id: str) -> str:
    """
    Gets the most predominant colour in an image.

    :param thumb_id: The image thumbnail ID
    :return: A hex code (including starting hash)
    """
    num_clusters = 5

    image = get_raw_image(thumb_id, width=150)
    ar = np.asarray(image)
    shape = ar.shape

    if len(shape) > 2:
        ar = ar.reshape(scipy.product(shape[:2]), shape[2]).astype(float)
    else:  # TODO Actually figure out what's going wrong here
        ar = ar.reshape(scipy.product(shape[:1]), shape[1]).astype(float)

    codes, dist = scipy.cluster.vq.kmeans(ar, num_clusters)

    vecs, dist = scipy.cluster.vq.vq(ar, codes)  # assign codes
    counts, bins = scipy.histogram(vecs, len(codes))  # count occurrences
    index_max = scipy.argmax(counts)  # find most frequent
    peak = codes[index_max]

    colour = '#'
    for c in peak:
        char = str(hex(int(c)))[2:]
        if len(char) == 1:
            char = '0' + char

        colour += char

    return colour


def get_complimentary_colour(hex_code: str) -> str:
    """
    Gets the inverse colour to a given hex code.

    :param hex_code: A hex colour with or without the starting hash
    :return: A hex code of the inverse colour, with the starting hash.
    """
    if hex_code.startswith('#'):
        hex_code = hex_code[1:]

    rgb = (hex_code[0:2], hex_code[2:4], hex_code[4:6])
    comp = ['%02X' % (255 - int(a, 16)) for a in rgb]
    return '#' + ''.join(comp)


def get_text_colour(hex_code: str) -> str:
    """
    Returns the configured dark or light colour
    depending on the background colour.

    A formula for brightness by the W3C is used to determine
    whether the given colour is light or dark.

    :param hex_code: The background hex code, with or without the starting hash.
    :return: A light or dark colour with the starting hash.
    """
    if hex_code.startswith('#'):
        hex_code = hex_code[1:]

    rgb = (int(hex_code[0:2], 16), int(hex_code[2:4], 16), int(hex_code[4:6], 16))

    # W3C formula for brightness
    brightness = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000

    # Brightness is from 0-255

    settings = app.get_settings()['colors']

    if brightness > 170:
        return settings['textDark']
    else:
        return settings['textLight']
