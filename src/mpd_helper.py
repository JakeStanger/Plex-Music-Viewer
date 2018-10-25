from typing import Optional


def get_sort_name(string: str) -> str:
    to_remove = ['The', 'A']

    for word in to_remove:
        if string.startswith(word):
            string = string[len(word):]

    return string


def generate_artist_key(song):
    pass


def generate_album_key(song):
    pass


def generate_track_key(song):
    pass


def get_genres_as_text(song) -> Optional[str]:
    if 'genre' not in song:
        return ''

    genres = song['genre']
    if isinstance(genres, str):
        return genres

    return ','.join(genres)
