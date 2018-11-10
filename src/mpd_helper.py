from typing import Optional


def get_genres_as_text(song) -> Optional[str]:
    if 'genre' not in song:
        return ''

    genres = song['genre']
    if isinstance(genres, str):
        return genres

    return ','.join(genres)
