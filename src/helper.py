import math
import string
from _md5 import md5
import secrets
import database as db
from flask import abort, Response


def generate_secret_key(length=64):
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))


def throw_error(num: int, error):
    """
    Throws an HTTP error
    :param num: The HTTP error number
    :param error: An error message
    """
    abort(Response(error, num))


def get_current_user() -> db.User:
    """
    Imports the current user from Flask and returns it.
    Used outside of requests where current_user is otherwise None.
    :return: The current user.
    """
    from flask_login import current_user
    return current_user


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


def get_sort_name(name: str) -> str:
    to_remove = ['The', 'A']

    for word in to_remove:
        if name.startswith(word + ' '):
            name = name[len(word + ' '):]

    return name


def get_numbers(value: str) -> int:
    return int(value[:8], 16)


def generate_artist_hash(name: str) -> int:
    return get_numbers(md5(name.encode('utf8')).hexdigest())


def generate_album_hash(name: str, artist_name: str) -> int:
    return get_numbers(md5(('%s%s' % (name, artist_name)).encode('utf8')).hexdigest())


def generate_track_hash(name: str, album_name: str, artist_name: str, relative_path: str) -> int:
    return get_numbers(md5(('%s%s%s%s' % (name, album_name, artist_name, relative_path)).encode('utf8')).hexdigest())
