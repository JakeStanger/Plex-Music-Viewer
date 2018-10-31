import os
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

import pmv
from db import Album


def get_image_path(album: Album, size: int) -> str:
    return 'images/%s_%r.jpg' % (album.id, size)


def _get_url_as_bytesio(url: str) -> BytesIO:
    return BytesIO(urlopen(url).read())


def _fetch_from_plex(album: Album) -> Optional[BytesIO]:
    """
    Queries the Plex server using the ID
    and fetches the set thumbnail for the item.

    :param album The album to find the cover for.
    :return: A BytesIO object of the image
    if one is found.
    """

    # TODO return none if not using plex

    settings = pmv.settings
    if not settings['serverToken']:
        return None

    thumb_id = '/' + str(album.plex_thumb)
    url = settings['serverAddress'] + thumb_id + "?X-Plex-Token=" + settings['serverToken']

    return _get_url_as_bytesio(url)


def _fetch_from_musicbrainz(album: Album, size) -> Optional[str]:
    """
    Looks up the album and artist on musicbrainz and
    fetches the front cover album art for it.

    :param album: The album to find the cover for.
    :return: The filename of the downloaded image
    if one was found.
    """
    release = mb.search_releases(artist=album.artist_name, release=album.name, limit=1)['release-list'][0]

    filename = get_image_path(album, size)

    try:
        with open(filename, 'wb') as f:
            f.write(mb.get_image_front(release['id'], size=size))
    except mb.ResponseError:  # Image not found
        return None

    return filename


def _fetch_from_lastfm(album: Album) -> Optional[BytesIO]:
    """
    Looks up the album on last.fm and fetches
    album art for it.

    Returns none if nothing is found or the
    last.fm key is not set.

    :param album: The album to find the cover for.
    :return: A BytesIO object of the image if
    one is found.
    """
    settings = pmv.settings
    if not settings['lastfm_key']:
        return None

    network = pl.LastFMNetwork(api_key=pmv.settings['lastfm_key'])

    album_search = pl.AlbumSearch(album.name, network)

    if album_search.get_total_result_count() == 0:
        return None

    # Get first result
    album = album_search.get_next_page()[0]

    url = album.get_cover_image()
    return _get_url_as_bytesio(url)


def _fetch_from_local(album: Album) -> Optional[str]:
    """
    Looks for images in the album directory.
    Checks each track in case they are in separated directories.
    Will return the first image it finds.

    :param album: The album to find the cover for.
    :return: The filename of the first image file
    found in a directory containing tracks from the
    given album, assuming one is found.
    """
    valid_images = [".jpg", ".gif", ".png", ".tga"]

    visited_paths = []
    for track in album.tracks:
        folder = os.path.dirname(track.downloadURL)

        if folder in visited_paths:
            continue

        visited_paths.append(folder)
        for f in os.listdir(folder):
            ext = os.path.splitext(f)[1]
            if ext.lower() not in valid_images:
                continue

            return os.path.join(folder, f)

    return None


def save_image_to_disk(album: Album, image: Image, width: int):
    """
    Writes the given image to disk using
    its friendly ID as the filename.

    :param album: The album associated with the image
    :param image: The image object
    :param width: The desired width of the image
    :return:
    """
    if not os.path.exists('images'):
        os.makedirs('images')

    image.save(get_image_path(album, width), str(width), 'PNG', quality=90)


def read_image_from_disk(album: Album, width: int):
    try:

        return Image.open(get_image_path(album, width), str(width))
    except FileNotFoundError:
        return None


def get_raw_image(album: Album, width: int=None) -> Image:
    cached = read_image_from_disk(album, width)
    if cached:
        return cached

    search_methods = pmv.settings['album_art_fetchers']
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

    save_image_to_disk(album, image, width)
    return image
    # except Exception as e:
    #     print(e)
    #     app.throw_error(400, "invalid thumb-id")


def get_image(album: Album, width: Optional[int]=None) -> BytesIO:
    image = get_raw_image(album, width)
    tmp_image = BytesIO()
    image.save(tmp_image, 'PNG', quality=90)
    tmp_image.seek(0)

    return tmp_image


def get_predominant_colour(album: Album) -> str:
    """
    Gets the most predominant colour in an image.

    :param album: The album associated with the image
    :return: A hex code (including starting hash)
    """
    num_clusters = 5

    image = get_raw_image(album, width=150)
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

    settings = pmv.get_settings()['colors']

    if brightness > 170:
        return settings['textDark']
    else:
        return settings['textLight']
