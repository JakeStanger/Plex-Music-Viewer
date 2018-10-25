from flask import abort, Response, request


def generate_secret_key(length=64):
    from base64 import b64encode
    from os import urandom

    random_bytes = urandom(length)
    return b64encode(random_bytes).decode('utf-8')


def throw_error(num, error):
    """
    Throws an HTTP error
    :param num: The HTTP error number
    :param error: An error message
    """
    abort(Response(error, num))
