from enum import Enum

from flask_sqlalchemy import SQLAlchemy

db: SQLAlchemy = SQLAlchemy()


def init(app):
    with app.app_context():
        db.init_app(app)
        db.create_all()


def session():
    return db.session


def database():
    return db


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
