import json
from enum import Enum
from os import path
from typing import List

from flask_login import UserMixin
from sqlalchemy import create_engine, Column, Integer, String, SmallInteger, Boolean, BigInteger, Date, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, session as orm_session
from sqlalchemy.orm.exc import NoResultFound
from plexapi.audio import Artist as PlexArtist, Album as PlexAlbum, Track as PlexTrack
from plexapi.media import MediaPart, Media

import helper

Base = declarative_base()

engine = None
SessionMaker: sessionmaker = None


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


def init():
    import pmv
    print("Initialising database engine")  # TODO Add logger
    global engine
    global SessionMaker
    db_settings = pmv.settings['database']
    engine = create_engine('mysql://%s:%s@%s:%s/%s'
                           % (db_settings['user'], db_settings['password'],
                              db_settings['hostname'], db_settings['port'], db_settings['database']))

    Base.metadata.create_all(engine)

    SessionMaker = sessionmaker()
    SessionMaker.configure(bind=engine)

    populate_db_from_plex()  # TODO Remove test code


class User(Base, UserMixin):
    __tablename__ = 'users_test'

    id = Column(Integer, primary_key=True)
    username = Column(String(32), nullable=False)
    password = Column(String(100), nullable=False)

    music_can_delete = Column(Boolean, default=False)
    music_can_transcode = Column(Boolean, default=False)
    music_can_upload = Column(Boolean, default=False)
    music_can_edit = Column(Boolean, default=False)
    music_can_download = Column(Boolean, default=False)
    music_can_view = Column(Boolean, default=True)

    movie_can_delete = Column(Boolean, default=False)
    movie_can_transcode = Column(Boolean, default=False)
    movie_can_upload = Column(Boolean, default=False)
    movie_can_edit = Column(Boolean, default=False)
    movie_can_download = Column(Boolean, default=False)
    movie_can_view = Column(Boolean, default=True)

    tv_can_delete = Column(Boolean, default=False)
    tv_can_transcode = Column(Boolean, default=False)
    tv_can_upload = Column(Boolean, default=False)
    tv_can_edit = Column(Boolean, default=False)
    tv_can_download = Column(Boolean, default=False)
    tv_can_view = Column(Boolean, default=True)

    is_admin = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)

    api_key = Column(String(64), nullable=True)

    authenticated = False

    def __repr__(self):
        return "<%d - %s>" % (self.id, self.username)

    def is_authenticated(self) -> bool:
        return self.authenticated

    def set_authenticated(self, auth: bool):
        self.authenticated = auth

    def has_permission(self, permission: Permission) -> bool:
        return getattr(self, permission.name)


class Artist(Base):
    __tablename__ = 'artists_test'

    id = Column(Integer, primary_key=True)

    name = Column(String(191), nullable=False)
    name_sort = Column(String(191))

    album_count = Column(SmallInteger)

    plex_id = Column(BigInteger, unique=True)
    plex_thumb = Column(BigInteger)

    mpd_id = Column(BigInteger, unique=True)

    albums = relationship('Album', back_populates='artist')
    tracks = relationship('Track', back_populates='artist')

    def __repr__(self):
        return "<%d - %s>" % (self.id, self.name)


class Album(Base):
    __tablename__ = 'albums_test'

    id = Column(Integer, primary_key=True)

    name = Column(String(191), nullable=False)
    name_sort = Column(String(191))

    artist_key = Column(Integer, ForeignKey('artists_test.id'))
    artist_name = Column(String(191))

    release_date = Column(Date)
    genres = Column(Text)

    track_count = Column(SmallInteger)

    plex_id = Column(BigInteger, unique=True)
    plex_thumb = Column(BigInteger)

    mpd_id = Column(BigInteger, unique=True)

    artist = relationship('Artist', back_populates='albums')
    tracks = relationship('Track', back_populates='album')

    def __repr__(self):
        return "<%d - %s>" % (self.id, self.name)

    def total_size(self):
        pass  # TODO Calculate total size


class Track(Base):
    __tablename__ = 'tracks_test'

    id = Column(Integer, primary_key=True)

    name = Column(String(191), nullable=False)
    name_sort = Column(String(191))

    artist_key = Column(Integer, ForeignKey('artists_test.id'))
    artist_name = Column(String(191))

    album_key = Column(Integer, ForeignKey('albums_test.id'))
    album_name = Column(String(191))

    duration = Column(Integer)

    track_num = Column(SmallInteger)
    disc_num = Column(SmallInteger)

    download_url = Column(Text)
    bitrate = Column(Integer)
    size = Column(BigInteger)
    format = Column(String(4))

    plex_id = Column(BigInteger, unique=True)

    mpd_id = Column(BigInteger, unique=True)

    artist = relationship('Artist', back_populates='tracks')
    album = relationship('Album', back_populates='tracks')

    def __repr__(self):
        return "<%d - %s>" % (self.id, self.name)


def _get_session() -> orm_session:
    global SessionMaker
    return SessionMaker()


def add_single(obj):
    session = _get_session()
    session.add(obj)
    session.commit()


def add_user(username, password):
    add_single(User(username=username, password=password, api_key=helper.generate_secret_key()))


def get_user(param: str) -> User:
    session = _get_session()
    try:
        if not param.isdigit():
            return session.query(User).filter_by(username=param).one()
        else:
            return session.query(User).filter_by(id=param).one()
    except NoResultFound as e:
        print(e)  # TODO Proper error handling


def get_artist_by_plex_key(session, plex_key: int) -> Artist:
    return session.query(Artist).filter_by(plex_id=plex_key).first()


def get_artist_by_name(session, name: str) -> Artist:
    return session.query(Artist).filter_by(name=name).first()


def get_album_by_plex_key(session, plex_key: int) -> Album:
    return session.query(Album).filter_by(plex_id=plex_key).first()


def get_album_by_name(session, name: str) -> Album:
    return session.query(Album).filter_by(name=name).first()


def get_track_by_plex_key(session, plex_key: int) -> Track:
    return session.query(Track).filter_by(plex_id=plex_key).first()


def base_key(key: str) -> int:
    return int(path.basename(key))


def populate_db_from_plex():
    import pmv
    session = _get_session()
    artists: List[PlexArtist] = pmv.music.all()
    for artist in artists:
        print(artist.title)
        artist_key = base_key(artist.key)
        albums: List[PlexAlbum] = artist.albums()

        artist_query = get_artist_by_plex_key(session, artist_key)
        if not artist_query:
             session.add(Artist(name=artist.title,
                                name_sort=artist.titleSort,
                                album_count=len(albums),
                                plex_id=artist_key,
                                plex_thumb=base_key(artist.thumb) if artist.thumb else None))
        for album in albums:
            print("\t" + album.title)
            album_key = base_key(artist.key)
            tracks: List[PlexTrack] = album.tracks()

            album_query = get_album_by_plex_key(session, album_key)
            if not album_query:
                session.add(Album(name=album.title,
                                  name_sort=album.titleSort,
                                  artist_key=get_artist_by_plex_key(session, artist_key).id,
                                  artist_name=artist.title,
                                  release_date=album.year,
                                  genres=','.join([genre.tag for genre in album.genres]),
                                  track_count=len(tracks),
                                  plex_id=album_key,
                                  plex_thumb=base_key(album.thumb)))

            for track in tracks:
                print("\t\t" + track.title)
                track_key = base_key(track.key)
                track_query = get_track_by_plex_key(session, artist_key)
                if not track_query:
                    media: Media = track.media[0]
                    track_part: MediaPart = [*track.iterParts()][0]

                    session.add(Track(name=track.title,
                                      name_sort=track.titleSort,
                                      artist_key=get_artist_by_plex_key(session, artist_key).id,
                                      artist_name=artist.title,
                                      album_key=get_album_by_plex_key(session, album_key).id,
                                      album_name=album.title,
                                      duration=track.duration,
                                      track_num=track.index,
                                      disc_num=track.parentIndex,
                                      download_url=track_part.file,
                                      bitrate=media.bitrate,
                                      size=track_part.size,
                                      format=media.audioCodec,
                                      plex_id=track_key))

    print("Committing session")
    session.commit()
