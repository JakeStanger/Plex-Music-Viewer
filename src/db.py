import operator
import os
from enum import Enum
from functools import reduce
from os import path
from timeit import default_timer as timer
from typing import List, Union

import mutagen
from flask_login import UserMixin
from plexapi.audio import Artist as PlexArtist, Album as PlexAlbum, Track as PlexTrack
from plexapi.media import MediaPart, Media
from flask_sqlalchemy import SQLAlchemy

import helper
import mpd_helper
from PersistentMPDClient import PersistentMPDClient

db: SQLAlchemy = SQLAlchemy()


def init(app):
    with app.app_context():
        db.init_app(app)
        db.create_all()


def session():
    return db.session


class Permission(Enum):
    music_can_delete = 0
    music_can_transcode = 1
    music_can_upload = 2
    music_can_edit = 3
    music_can_download = 4
    music_can_view = 5

    movie_can_delete = 6
    movie_can_transcode = 7
    movie_can_upload = 8
    movie_can_edit = 9
    movie_can_download = 10
    movie_can_view = 11

    tv_can_delete = 12
    tv_can_transcode = 13
    tv_can_upload = 14
    tv_can_edit = 15
    tv_can_download = 16
    tv_can_view = 17


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), nullable=False)
    password = db.Column(db.String(100), nullable=False)

    music_can_delete = db.Column(db.Boolean, default=False)
    music_can_transcode = db.Column(db.Boolean, default=False)
    music_can_upload = db.Column(db.Boolean, default=False)
    music_can_edit = db.Column(db.Boolean, default=False)
    music_can_download = db.Column(db.Boolean, default=False)
    music_can_view = db.Column(db.Boolean, default=True)

    movie_can_delete = db.Column(db.Boolean, default=False)
    movie_can_transcode = db.Column(db.Boolean, default=False)
    movie_can_upload = db.Column(db.Boolean, default=False)
    movie_can_edit = db.Column(db.Boolean, default=False)
    movie_can_download = db.Column(db.Boolean, default=False)
    movie_can_view = db.Column(db.Boolean, default=True)

    tv_can_delete = db.Column(db.Boolean, default=False)
    tv_can_transcode = db.Column(db.Boolean, default=False)
    tv_can_upload = db.Column(db.Boolean, default=False)
    tv_can_edit = db.Column(db.Boolean, default=False)
    tv_can_download = db.Column(db.Boolean, default=False)
    tv_can_view = db.Column(db.Boolean, default=True)

    is_admin = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)

    api_key = db.Column(db.String(64), nullable=True)

    authenticated = False

    def __repr__(self):
        return "<%d - %s>" % (self.id, self.username)

    def is_authenticated(self) -> bool:
        return self.authenticated

    def set_authenticated(self, auth: bool):
        self.authenticated = auth

    def has_permission(self, permission: Permission) -> bool:
        return getattr(self, permission.name)


class Artist(db.Model):
    __tablename__ = 'artists'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(191), nullable=False)
    name_sort = db.Column(db.String(191))

    album_count = db.Column(db.SmallInteger)

    plex_id = db.Column(db.BigInteger, unique=True)
    plex_thumb = db.Column(db.BigInteger)

    mpd_id = db.Column(db.BigInteger, unique=True)

    albums: list = db.relationship('Album', back_populates='artist')
    tracks: list = db.relationship('Track', back_populates='artist')

    def __repr__(self):
        return "<%d - %s>" % (self.id, self.name)


class Album(db.Model):
    __tablename__ = 'albums'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(191), nullable=False)
    name_sort = db.Column(db.String(191))

    artist_key = db.Column(db.Integer, db.ForeignKey('artists.id'))
    artist_name = db.Column(db.String(191))

    release_date = db.Column(db.Date)
    genres = db.Column(db.Text)

    track_count = db.Column(db.SmallInteger)

    plex_id = db.Column(db.BigInteger, unique=True)
    plex_thumb = db.Column(db.BigInteger)

    mpd_id = db.Column(db.BigInteger, unique=True)

    artist = db.relationship('Artist', back_populates='albums')

    tracks: list = db.relationship('Track', back_populates='album')

    def __repr__(self):
        return "<%d - %s>" % (self.id, self.name)

    def total_size(self):
        pass
        return reduce(operator.add, [track.size for track in self.tracks])


class Track(db.Model):
    __tablename__ = 'tracks'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(191), nullable=False)
    name_sort = db.Column(db.String(191))

    artist_key = db.Column(db.Integer, db.ForeignKey('artists.id'))
    artist_name = db.Column(db.String(191))

    album_key = db.Column(db.Integer, db.ForeignKey('albums.id'))
    album_name = db.Column(db.String(191))

    duration = db.Column(db.BigInteger)

    track_num = db.Column(db.SmallInteger)
    disc_num = db.Column(db.SmallInteger)

    download_url = db.Column(db.Text)
    bitrate = db.Column(db.Integer)
    size = db.Column(db.BigInteger)
    format = db.Column(db.String(4))

    plex_id = db.Column(db.BigInteger, unique=True)

    mpd_id = db.Column(db.BigInteger, unique=True)

    artist = db.relationship('Artist', back_populates='tracks')
    album = db.relationship('Album', back_populates='tracks')

    def __repr__(self):
        return "<%d - %s>" % (self.id, self.name)


def add_single(obj):
    db.session.add(obj)
    db.session.commit()


def get_users():
    return db.session.query(User).all()


def add_user(username, password):
    add_single(User(username=username, password=password, api_key=helper.generate_secret_key()))


def get_user_by_id(key: int):
    return db.session.query(User).filter_by(id=key).first()


def get_user_by_username(username: str):
    return db.session.query(User).filter_by(username=username).first()


def edit_user_by_id(key: int, fields: dict):
    user: User = get_user_by_id(key)
    for key in fields:
        setattr(user, key, fields[key])


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


def delete_user_by_username(username: str, restore=False):
    user: User = get_user_by_username(username)
    user.is_deleted = not restore


def get_artists():
    return db.session.query(Artist).all()


def get_artist_by_id(key: int) -> Artist:
    return db.session.query(Artist).filter_by(id=key).first()


def get_artist_by_plex_key(plex_key: int) -> Artist:
    return db.session.query(Artist).filter_by(plex_id=plex_key).first()


def get_artist_by_mpd_key(mpd_key: int) -> Artist:
    return db.session.query(Artist).filter_by(mpd_id=mpd_key).first()


def get_artist_by_name(name: str) -> Artist:
    return db.session.query(Artist).filter_by(name=name).first()


def get_album_by_id(key: int) -> Album:
    return db.session.query(Album).filter_by(id=key).first()


def get_album_by_plex_key(plex_key: int) -> Album:
    return db.session.query(Album).filter_by(plex_id=plex_key).first()


def get_album_by_mpd_key(mpd_key: int) -> Album:
    return db.session.query(Album).filter_by(mpd_id=mpd_key).first()


def get_album_by_name(artist_name: str, name: str) -> Album:
    return db.session.query(Album).filter_by(name=name, artist_name=artist_name).first()


def get_track_by_id(key: int) -> Track:
    return db.session.query(Track).filter_by(plex_id=key).first()


def get_track_by_plex_key(plex_key: int) -> Track:
    return db.session.query(Track).filter_by(plex_id=plex_key).first()


def get_track_by_mpd_key(mpd_key: int) -> Track:
    return db.session.query(Track).filter_by(mpd_id=mpd_key).first()


def base_key(key: str) -> int:
    return int(path.basename(key))


def populate_db_from_plex():
    import pmv

    start_time = timer()

    artists: List[PlexArtist] = pmv.music.all()
    for artist in artists:
        print(artist.title)
        artist_key = base_key(artist.key)
        albums: List[PlexAlbum] = artist.albums()

        artist_query = get_artist_by_plex_key(artist_key)
        if not artist_query:
            db.session.add(Artist(name=artist.title,
                                  name_sort=artist.titleSort,
                                  album_count=len(albums),
                                  plex_id=artist_key,
                                  plex_thumb=base_key(artist.thumb) if artist.thumb else None))
            artist_query = get_artist_by_plex_key(artist_key)
        for album in albums:
            print('┣ ' + album.title)
            album_key = base_key(album.key)
            tracks: List[PlexTrack] = album.tracks()

            album_query = get_album_by_plex_key(album_key)
            if not album_query:
                db.session.add(Album(name=album.title,
                                     name_sort=album.titleSort,
                                     artist_key=artist_query.id,
                                     artist_name=artist.title,
                                     release_date=album.year,
                                     genres=','.join([genre.tag for genre in album.genres]),
                                     track_count=len(tracks),
                                     plex_id=album_key,
                                     plex_thumb=base_key(album.thumb)))
                album_query = get_album_by_plex_key(album_key)

            for track in tracks:
                print("┃ \t┣ " + track.title)
                track_key = base_key(track.key)
                track_query = get_track_by_plex_key(artist_key)
                if not track_query:
                    media: Media = track.media[0]
                    track_part: MediaPart = [*track.iterParts()][0]

                    db.session.add(Track(name=track.title,
                                         name_sort=track.titleSort,
                                         artist_key=artist_query.id,
                                         artist_name=artist.title,
                                         album_key=album_query.id,
                                         album_name=album.title,
                                         duration=track.duration,
                                         track_num=track.index,
                                         disc_num=track.parentIndex,
                                         download_url=track_part.file,
                                         bitrate=media.bitrate,
                                         size=track_part.size,
                                         format=media.audioCodec,
                                         plex_id=track_key))

    print("\nFinished constructing db.session in %r seconds" % round(timer() - start_time))
    print("Committing db.session.\n")
    db.session.commit()


def _get_mpd_key(data, key):
    """
    Since MPD supports any tag being a list,
    we want to just get the first one.
    Most of the time this is due to tagging issues
    """
    prop = data[key]
    if isinstance(prop, list):
        return prop[0]

    return prop


def populate_db_from_mpd():
    import pmv

    start_time = timer()

    music_library = pmv.settings['music_library']
    unknown_album = "[Unknown Album]"

    client = PersistentMPDClient(host='localhost', port=6600)  # TODO Add mpd settings to config

    library_dict = {}

    library = client.listallinfo()
    # Begin by assembling a dictionary
    print("Assembling dictionary. Please wait...")
    for song in library:
        # Make sure this is a song and not a directory
        if 'artist' in song:
            artist = song['artist']
            if artist not in library_dict:
                library_dict[artist] = {}

            # Handle songs with missing album tag
            if 'album' in song:
                album = song['album']
            else:
                album = unknown_album

            if album not in library_dict[artist]:
                # Date error checking
                if 'date' in song:
                    date = song['date'].replace('.', '-')
                    if '-' not in date:
                        date = '%s-01-01' % date
                else:
                    date = None  # Don't write anything for missing dates

                library_dict[artist][album] = {
                    'date': date,
                    'songs': []
                }
            if 'genres' not in library_dict[artist][album]:
                library_dict[artist][album]['genres'] = []
            library_dict[artist][album]['genres'].append(mpd_helper.get_genres_as_text(song))

            # Deduplicate
            library_dict[artist][album]['genres'] = list(set(library_dict[artist][album]['genres']))

            if 'track' not in song:
                song['track'] = 1
            if 'disc' not in song:
                song['disc'] = 1

            library_dict[artist][album]['songs'].append({key: _get_mpd_key(song, key) for key in song})

    for artist in library_dict:
        print(artist)
        albums = library_dict[artist]
        artist_id = mpd_helper.generate_artist_key(artist)

        artist_query = get_artist_by_mpd_key(artist_id)
        if not artist_query:
            db.session.add(Artist(name=artist,
                                  name_sort=mpd_helper.get_sort_name(artist),
                                  album_count=len(albums),
                                  mpd_id=artist_id))
            artist_query = get_artist_by_mpd_key(artist_id)

        for album in albums:
            print('┣ ' + album)
            album_data = albums[album]
            album_id = mpd_helper.generate_album_key(album, artist)
            tracks = album_data['songs']

            album_query = get_album_by_mpd_key(album_id)
            if not album_query:
                genre_list = filter(lambda x: len(x) > 0, album_data['genres'])
                db.session.add(Album(name=album,
                                     name_sort=mpd_helper.get_sort_name(album),
                                     artist_key=artist_query.id,
                                     artist_name=artist,
                                     release_date=album_data['date'],
                                     genres=','.join([genre for genre in genre_list]),
                                     track_count=len(tracks),
                                     mpd_id=album_id))
                album_query = get_album_by_mpd_key(album_id)

            for track in tracks:
                track_title = track['title']
                print("┃ \t┣ " + track_title)

                full_path = music_library + track['file']
                track_key = mpd_helper.generate_track_key(track_title, album, artist, full_path)

                track_query = get_track_by_mpd_key(track_key)
                if not track_query:
                    db.session.add(Track(name=track_title,
                                         name_sort=mpd_helper.get_sort_name(track_title),
                                         artist_key=artist_query.id,
                                         artist_name=artist,
                                         album_key=album_query.id,
                                         album_name=album,
                                         duration=track['duration'] * 1000,  # Store time in ms
                                         track_num=track['track'],
                                         disc_num=track['disc'],
                                         download_url=full_path,
                                         bitrate=mutagen.File(full_path).info.bitrate / 1000,  # Store bitrate in kbps
                                         size=os.path.getsize(full_path),
                                         format=full_path.rpartition('.')[-1].lower(),
                                         mpd_id=track_key))

    print("\nFinished constructing db.session in %r seconds" % round(timer() - start_time))
    print("Committing db.session.\n")
    db.session.commit()
