import os
from io import BytesIO
from typing import Optional, List, Tuple
from urllib.request import urlopen
from urllib.error import HTTPError

import musicbrainzngs as mb
import numpy as np
import pylast as pl
import scipy
import scipy.cluster
import scipy.misc
from PIL import Image
from database.models import Album
from colorharmonies import Color, complementaryColor


def get_image_path(album: Album, size: int = None) -> str:
    if not album.id:
        return '/etc/pmv/images/%s-%s_%s.jpg' % (album.artist_name, album.name, size if size else 'full')
    return '/etc/pmv/images/%s_%s.jpg' % (album.id, size if size else 'full')


def _get_url_as_bytesio(url: str) -> Optional[BytesIO]:
    try:
        return BytesIO(urlopen(url).read())
    except HTTPError:
        return None


def _fetch_from_plex(album: Album, width: int) -> Optional[BytesIO]:
    """
    Queries the Plex server using the ID
    and fetches the set thumbnail for the item.

    :param album The album to find the cover for.
    :return: A BytesIO object of the image
    if one is found.
    """
    import pmv

    settings = pmv.settings
    if not settings['backends']['plex']['server_token']:
        return None

    url = "%s/library/metadata/%s/thumb/%s/%s" % (settings['backends']['plex']['server_address'],
                                                  album.plex_id, album.plex_thumb,
                                                  "?X-Plex-Token=" + settings['backends']['plex']['server_token'])

    return _get_url_as_bytesio(url)


def _fetch_from_musicbrainz(album: Album, width: int) -> Optional[str]:
    """
    Looks up the album and artist on musicbrainz and
    fetches the front cover album art for it.

    :param album: The album to find the cover for.
    :return: The filename of the downloaded image
    if one was found.
    """
    releases = mb.search_releases(artist=album.artist_name, release=album.name, limit=10)['release-list']
    filename = get_image_path(album, width)

    with open(filename, 'wb') as f:
        cover = None
        i = 0
        while not cover and i < len(releases):
            try:
                cover = mb.get_image_front(releases[i]['id'], size=width)
            except mb.ResponseError:
                i += 1
        if cover:
            f.write(cover)

    return filename if cover else None


def _fetch_from_lastfm(album: Album, width: int) -> Optional[BytesIO]:
    """
    Looks up the album on last.fm and fetches
    album art for it.

    Returns none if nothing is found or the
    last.fm key is not set.

    :param album: The album to find the cover for.
    :return: A BytesIO object of the image if
    one is found.
    """
    import pmv
    settings = pmv.settings
    if not settings['lastfm_key']:
        return None

    network = pl.LastFMNetwork(api_key=pmv.settings['lastfm_key'])

    album_search = pl.AlbumSearch(album.name, network)

    if album_search.get_total_result_count() == 0:
        return None

    # Get first result
    search_results = album_search.get_next_page()
    if len(search_results) > 0:
        album = album_search.get_next_page()[0]

        url = album.get_cover_image()
        return _get_url_as_bytesio(url) if url else None
    else:
        return None


def _fetch_from_local(album: Album, width: int) -> Optional[str]:
    """
    Looks for images in the album directory.
    Checks each track in case they are in separated directories.
    Will return the first image it finds.

    :param album: The album to find the cover for.
    :return: The filename of the first image file
    found in a directory containing tracks from the
    given album, assuming one is found.
    """
    import pmv

    valid_images = [".jpg", ".gif", ".png", ".tga"]

    visited_paths = []
    for track in album.tracks:
        folder = pmv.settings['music_library'] + os.path.dirname(track.download_url)

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

    image.save(get_image_path(album, width), format='PNG', quality=90)


def read_image_from_disk(album: Album, width: int):
    try:
        path = get_image_path(album, width)
        return Image.open(path)
    except FileNotFoundError:
        return None
    except OSError:
        return None


def get_raw_image(album: Album, width: int = None) -> Image:
    import pmv
    cached = read_image_from_disk(album, width)
    if cached:
        return cached

    search_methods = pmv.settings['album_art_fetchers']
    i = 0
    file = None

    # Call local functions for each fetching method until a result is found
    while not file and i < len(search_methods):
        file = globals()['_fetch_from_%s' % search_methods[i]](album, width)
        i += 1

    if not file:
        return None

    image = Image.open(file)

    if width:
        size = int(width), int(width)
        image.thumbnail(size, Image.ANTIALIAS)

    save_image_to_disk(album, image, width)
    return image
    # except Exception as e:
    #     print(e)
    #     app.throw_error(400, "invalid thumb-id")


def get_image(album: Album, width: Optional[int] = None) -> Optional[BytesIO]:
    image = get_raw_image(album, width)
    if image:
        tmp_image = BytesIO()
        image.save(tmp_image, 'PNG', quality=90)
        tmp_image.seek(0)

        return tmp_image
    else:
        return None


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


def get_rgb(hex_code: str) -> Tuple[int, int, int]:
    hex_code = hex_code.strip('#')

    return int(hex_code[0:2], 16), int(hex_code[2:4], 16), int(hex_code[4:6], 16)


def get_hex(rgb: Tuple[int, int, int]) -> str:
    return '#%02x%02x%02x' % (rgb[0], rgb[1], rgb[2])


def get_text_colour(hex_code: str) -> str:
    """
    Returns the configured dark or light colour
    depending on the background colour.

    A formula for brightness by the W3C is used to determine
    whether the given colour is light or dark.

    :param hex_code: The background hex code, with or without the starting hash.
    :return: A light or dark colour with the starting hash.
    """
    import pmv

    r, g, b = get_rgb(hex_code)

    # W3C formula for brightness
    brightness = (r * 299 + g * 587 + b * 114) / 1000

    # Brightness is from 0-255

    settings = pmv.settings['colors']

    if brightness > 170:
        return settings['text_dark']
    else:
        return settings['text_light']


def get_button_colour(hex_code: str) -> str:
    rgb = get_rgb(hex_code)
    color = Color(rgb, "", "")

    palette = complementaryColor(color)
    return get_hex(palette)
