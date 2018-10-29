import math

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
