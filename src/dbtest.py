from json import load

from flask_login import UserMixin
from sqlalchemy import create_engine, Column, Integer, String, SmallInteger, Boolean, BigInteger, Date, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

settings = load(open('../settings.json'))
db_settings = settings['database']

engine = create_engine('mysql://%s:%s@%s:%s/%s'
                       % (db_settings['user'], db_settings['password'],
                          db_settings['hostname'], db_settings['port'], db_settings['database']))
Base = declarative_base()


class User(Base, UserMixin):
    __tablename__ = 'users_test'

    id = Column(Integer, primary_key=True)
    username = Column(String(32), nullable=False)
    password = Column(String(100), nullable=False)

    music_can_delete = Column(Boolean, default=False)
    music_can_transcode = Column(Boolean, default=False)
    music_can_upload = Column(Boolean, default=False)
    music_can_edit = Column(Boolean, default=False)
    music_can_download = Column(Boolean, default=True)
    music_can_view = Column(Boolean, default=True)

    movie_can_delete = Column(Boolean, default=False)
    movie_can_transcode = Column(Boolean, default=False)
    movie_can_upload = Column(Boolean, default=False)
    movie_can_edit = Column(Boolean, default=False)
    movie_can_download = Column(Boolean, default=True)
    movie_can_view = Column(Boolean, default=True)

    tv_can_delete = Column(Boolean, default=False)
    tv_can_transcode = Column(Boolean, default=False)
    tv_can_upload = Column(Boolean, default=False)
    tv_can_edit = Column(Boolean, default=False)
    tv_can_download = Column(Boolean, default=True)
    tv_can_view = Column(Boolean, default=True)

    is_admin = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)

    authenticated = False

    def __repr__(self):
        return "<%d - %s>" % (self.id, self.username)

    def is_authenticated(self) -> bool:
        return self.authenticated

    def set_authenticated(self, auth: bool):
        self.authenticated = auth


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


Base.metadata.create_all(engine)

test_guy = User(username="Mr Testy", password="bfjos ;'W")

Session = sessionmaker()
Session.configure(bind=engine)

session = Session()

session.add(test_guy)
session.commit()
