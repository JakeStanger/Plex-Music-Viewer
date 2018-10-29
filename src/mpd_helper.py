from typing import Optional
from hashlib import md5


def get_sort_name(string: str) -> str:
    to_remove = ['The', 'A']

    for word in to_remove:
        if string.startswith(word + ' '):
            string = string[len(word + ' '):]

    return string


def get_numbers(value: str) -> int:
    return int(value[:8], 16)


def generate_artist_key(name: str) -> int:
    return get_numbers(md5(name.encode('utf8')).hexdigest())


def generate_album_key(name: str, artist: str) -> int:
    return get_numbers(md5(('%s%s' % (name, artist)).encode('utf8')).hexdigest())


def generate_track_key(name: str, album: str, artist: str, full_path: str) -> int:
    return get_numbers(md5(('%s%s%s%s' % (name, album, artist, full_path)).encode('utf8')).hexdigest())


def get_genres_as_text(song) -> Optional[str]:
    if 'genre' not in song:
        return ''

    genres = song['genre']
    if isinstance(genres, str):
        return genres

    return ','.join(genres)
