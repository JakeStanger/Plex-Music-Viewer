from typing import Union, List

import helper
from .db import database, Permission
from .models import User, Artist, Album, Track

db = database()


def add_single(obj):
    db.session.add(obj)
    db.session.commit()


def get_users(include_deleted: bool = False):
    if include_deleted:
        return db.session.query(User).all()
    else:
        return db.session.query(User).filter_by(is_deleted=False).all()


def add_user(username, password):
    # TODO Look into why PyCharm is flagging this
    # noinspection PyArgumentList
    add_single(User(username=username, password=password, api_key=helper.generate_secret_key()))


def get_user_by_id(key: int):
    return db.session.query(User).filter_by(id=key).first()


def get_user_by_api_key(api_key: str):
    return db.session.query(User).filter_by(api_key=api_key).first()


def get_user_by_username(username: str):
    return db.session.query(User).filter_by(username=username).first()


def edit_user_by_id(key: int, fields: dict):
    user: User = get_user_by_id(key)
    for key in fields:
        if key == 'id' or key == 'action':
            continue

        value = fields[key]

        if '_perms' in key and isinstance(value, str):
            start = 0
            if key == 'movie_perms':
                start = 6
            elif key == 'tv_perms':
                start = 12

            for i in range(start, start + 6):
                setattr(user, Permission(i).name, value[i - start] != '-')

        if key == 'is_admin' and isinstance(value, str):
            value = value == 'True'  # Any string passed other than 'True' should never be interpreted as true

        setattr(user, key, value)


def get_user(param: Union[str, int]) -> User:
    """
    Used by flask-login.
    Accepts username or user ID.
    """
    if not param.isdigit():
        return get_user_by_username(param)
    else:
        return get_user_by_id(param)


def delete_user_by_id(key: int, restore=False):
    user: User = get_user_by_id(key)
    user.is_deleted = not restore
    db.session.commit()


def delete_user_by_username(username: str, restore=False):
    user: User = get_user_by_username(username)
    user.is_deleted = not restore
    db.session.commit()


def get_artists():
    return db.session.query(Artist).all()


def get_artist_by_id(key: int) -> Artist:
    return db.session.query(Artist).filter_by(id=key).first()


def get_artist_by_plex_key(plex_key: int) -> Artist:
    return db.session.query(Artist).filter_by(plex_id=plex_key).first()


def get_artist_by_hash(hash_key: int) -> Artist:
    return db.session.query(Artist).filter_by(hash=hash_key).first()


def get_artist_by_name(name: str) -> Artist:
    return db.session.query(Artist).filter_by(name=name).first()


def get_artists_by_name(query: str) -> List[Artist]:
    return db.session.query(Artist).filter(Artist.name.ilike('%' + query + '%')).all()


def get_album_by_id(key: int) -> Album:
    return db.session.query(Album).filter_by(id=key).first()


def get_album_by_plex_key(plex_key: int) -> Album:
    return db.session.query(Album).filter_by(plex_id=plex_key).first()


def get_album_by_hash(hash_key: int) -> Album:
    return db.session.query(Album).filter_by(hash=hash_key).first()


def get_album_by_name(artist_name: str, name: str) -> Album:
    return db.session.query(Album).filter_by(name=name, artist_name=artist_name).first()


def get_albums_by_name(query: str) -> List[Album]:
    return db.session.query(Album).filter(Album.name.ilike('%' + query + '%')).all()


def get_track_by_id(key: int) -> Track:
    return db.session.query(Track).filter_by(id=key).first()


def get_track_by_plex_key(plex_key: int) -> Track:
    return db.session.query(Track).filter_by(plex_id=plex_key).first()


def get_track_by_hash(hash_key: int) -> Track:
    return db.session.query(Track).filter_by(hash=hash_key).first()


def get_tracks_by_name(query: str) -> List[Track]:
    return db.session.query(Track).filter(Track.name.ilike('%' + query + '%')).all()
