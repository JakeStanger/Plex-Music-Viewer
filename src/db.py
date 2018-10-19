from enum import Enum

from flask_login import UserMixin
from sqlalchemy import create_engine, Column, Integer, String, SmallInteger, Boolean, BigInteger, Date, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, session as orm_session
from sqlalchemy.orm.exc import NoResultFound
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
        print(getattr(self, permission.name))
        return getattr(self, permission.name)


class Artist(Base):
    __tablename__ = 'artists_test'

    id = Column(Integer, primary_key=True)

    name = Column(String(256), nullable=False)
    name_sort = Column(String(256))

    album_count = Column(SmallInteger)

    plex_id = Column(BigInteger)
    plex_thumb = Column(BigInteger)

    mpd_id = Column(BigInteger)

    def __repr__(self):
        return "<%d - %s>" % (self.id, self.name)


class Album(Base):
    __tablename__ = 'albums_test'

    id = Column(Integer, primary_key=True)

    name = Column(String(256), nullable=False)
    name_sort = Column(String(256))

    artist_key = Column(Integer, ForeignKey('artists_test.id'))
    artist_name = Column(String(256))

    release_date = Column(Date)
    genres = Column(Text)

    track_count = Column(SmallInteger)
    total_size = Column(BigInteger)

    plex_id = Column(BigInteger)
    plex_thumb = Column(BigInteger)

    mpd_id = Column(BigInteger)

    artist = relationship('Artist')

    def __repr__(self):
        return "<%d - %s>" % (self.id, self.name)


class Track(Base):
    __tablename__ = 'track_test'

    id = Column(Integer, primary_key=True)

    name = Column(String(256), nullable=False)
    name_sort = Column(String(256))

    artist_key = Column(Integer, ForeignKey('artists_test.id'))
    artist_name = Column(String(256))

    album_key = Column(Integer, ForeignKey('albums_test.id'))
    album_name = Column(String(256))

    duration = Column(Integer)

    track_num = Column(SmallInteger)
    disc_num = Column(SmallInteger)

    download_url = Column(Text)
    bitrate = Column(Integer)
    size = Column(BigInteger)
    format = Column(String(4))

    plex_id = Column(BigInteger)

    mpd_id = Column(BigInteger)

    artist = relationship('Artist')
    album = relationship('Album')

    def __repr__(self):
        return "<%d - %s>" % (self.id, self.name)


def _get_session() -> orm_session:
    global SessionMaker
    return SessionMaker()


def add_single(obj):
    session = _get_session()
    session.add(obj)
    session.commit()


def get_user(param: str) -> User:
    session = _get_session()
    try:
        if not param.isdigit():
            return session.query(User).filter_by(username=param).one()
        else:
            return session.query(User).filter_by(id=param).one()
    except NoResultFound as e:
        print(e)  # TODO Proper error handling
