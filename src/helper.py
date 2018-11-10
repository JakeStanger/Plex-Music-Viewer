import math
from _md5 import md5

from flask import abort, Response


def generate_secret_key(length=64):
    from base64 import b64encode
    from os import urandom

    random_bytes = urandom(length)
    return b64encode(random_bytes).decode('utf-8')


def throw_error(num: int, error):
    """
    Throws an HTTP error
    :param num: The HTTP error number
    :param error: An error message
    """
    abort(Response(error, num))


def format_size(size: int) -> str:
    sizes = ['B', 'kiB', 'MiB', 'GiB', 'TiB']
    if size == 0:
        return '0B'

    i = int(math.floor(math.log(size) / math.log(1024)))
    return ('%.3g' % (size / math.pow(1024, i))) + ' ' + sizes[i]


def format_duration(duration: int) -> str:
    minutes = math.floor(duration / 60000)
    seconds = math.floor((duration % 60000) / 1000)
    return str(minutes) + ":" + ('0' if seconds < 10 else '') + str(seconds)


def get_sort_name(string: str) -> str:
    to_remove = ['The', 'A']

    for word in to_remove:
        if string.startswith(word + ' '):
            string = string[len(word + ' '):]

    return string


def get_numbers(value: str) -> int:
    return int(value[:8], 16)


def generate_artist_hash(name: str) -> int:
    return get_numbers(md5(name.encode('utf8')).hexdigest())


def generate_album_hash(name: str, artist: str) -> int:
    return get_numbers(md5(('%s%s' % (name, artist)).encode('utf8')).hexdigest())


def generate_track_hash(name: str, album: str, artist: str, full_path: str) -> int:
    return get_numbers(md5(('%s%s%s%s' % (name, album, artist, full_path)).encode('utf8')).hexdigest())
