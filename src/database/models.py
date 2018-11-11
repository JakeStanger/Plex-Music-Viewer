import operator
from functools import reduce

from flask_login import UserMixin

from .db import Permission, database

db = database()


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

    lastfm_username = db.Column(db.String(16), nullable=True)

    playlists = db.relationship('Playlist', back_populates='creator')

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

    hash = db.Column(db.BigInteger, unique=True)

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

    hash = db.Column(db.BigInteger, unique=True)

    artist = db.relationship('Artist', back_populates='albums')

    tracks: list = db.relationship('Track', back_populates='album')

    def __repr__(self):
        return "<%d - %s>" % (self.id, self.name)

    def total_size(self):
        pass
        return reduce(operator.add, [track.size for track in self.tracks])


playlist_track = db.Table('playlist_track', db.metadata,
                          db.Column('track_id', db.ForeignKey('tracks.id'), primary_key=True),
                          db.Column('playlist_id', db.ForeignKey('playlists.id'), primary_key=True))


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

    hash = db.Column(db.BigInteger, unique=True)

    artist = db.relationship('Artist', back_populates='tracks')
    album = db.relationship('Album', back_populates='tracks')

    playlists = db.relationship('Playlist', secondary=playlist_track, back_populates='tracks')

    def __repr__(self):
        return "<%d - %s>" % (self.id, self.name)


class Playlist(db.Model):
    __tablename__ = "playlists"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(191), nullable=False)

    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    creator = db.relationship('User', back_populates='playlists')
    tracks = db .relationship('Track', secondary=playlist_track, back_populates='playlists')
