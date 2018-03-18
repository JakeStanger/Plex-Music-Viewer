from os import path
from urllib.parse import quote

from flaskext.mysql import MySQL
from plexapi.audio import Artist, Album, Track
import plex_helper as ph
import app

mysql = None
_cache = []


def init():
    global mysql
    mysql = MySQL()
    mysql.init_app(app.get_app())


def get_cache():
    return _cache


def insert_into_cache(data: dict):
    _cache.append(data)


def clear_cache():
    global _cache
    _cache = []

class Value:
    def __init__(self, column, value):
        self.column = column
        self.value = value

    def __repr__(self):
        return "%s: %s" % (self.column, self.value)


def call_proc(proc: str, values):
    global mysql
    if not mysql:
        init()

    conn = mysql.connect()
    cursor = conn.cursor()

    cursor.callproc('sp_createUser', values)

    data = cursor.fetchall()
    conn.close()

    return data


def exec_sql(query: str, fetch_one: bool = False, fetch_all: bool = False, commit: bool = False):
    global mysql
    if not mysql:
        init()

    conn = mysql.connect()
    cursor = conn.cursor()

    cursor.execute(query)

    if commit:
        conn.commit()

    if fetch_one:
        return cursor.fetchone()
    if fetch_all:
        return cursor.fetchall()

    conn.close()


def get_one(table: str, columns: list = None, conditions: list = None):
    return exec_sql("SELECT %s FROM %s" % (','.join(col for col in columns) if columns else '*', table)
                    + " WHERE %s" % ' AND '.join("%s='%s'" % (condition.column, condition.value)
                                                 for condition in conditions) if conditions else '', fetch_one=True)


def get_all(table: str, columns: list = None, conditions: list = None):
    return exec_sql("SELECT %s FROM %s" % (','.join(col for col in columns) if columns else '*', table)
                    + " WHERE %s" % ' AND '.join("%s='%s'" % (condition.column, condition.value)
                                                 for condition in conditions) if conditions else '', fetch_all=True)


def insert_direct(table: str, values: list, overwrite=False):
    exec_sql("%s INTO %s VALUES (%s)" % ('REPLACE' if overwrite else 'INSERT', table,
                                         ','.join("'%s'" % value.value for value in values)), commit=True)


def insert_specific(table: str, values: list, overwrite=False):
    exec_sql("%s INTO %s (%s) VALUES (%s)" % ('REPLACE' if overwrite else 'INSERT', table,
                                              ','.join(value.column for value in values),
                                              ','.join('%s' % value.value for value in values)), commit=True)


def update(table: str, values: list, condition: Value = None):
    exec_sql("UPDATE %s SET %s" % (table, ','.join("%s='%s'" % (value.column, value.value) for value in values))
             + " WHERE %s=%s" % (condition.column, condition.value) if condition else '', commit=True)


def delete(table: str, condition: Value = None):
    exec_sql("DELETE FROM %s" % table
             + " WHERE %s='%s'" % (condition.column, condition.value) if condition else '', commit=True)


def get_wrapper_information(wrapper, type):
    if type == 'ARTIST':
        return [
            Value('library_key', app.key_num(wrapper.key)),
            Value('name', wrapper.title.replace("'", "%27")),
            Value('name_sort', wrapper.titleSort.replace("'", "%27")),
            Value('thumb', wrapper.basename(wrapper.thumb) if wrapper.thumb else 0),
            Value('album_count', wrapper.num_albums)
        ]
    elif type == 'ALBUM':
        return [
            Value('library_key', app.key_num(wrapper.key)),
            Value('name', wrapper.title.replace("'", "%27")),
            Value('name_sort', wrapper.titleSort.replace("'", "%27")),
            Value('artist_key', app.key_num(wrapper.parentKey)),
            Value('year', wrapper.year),
            Value('thumb', path.basename(wrapper.thumb) if wrapper.thumb else 0),
            Value('track_count', wrapper.num_tracks),
            Value('total_size', wrapper.total_size)
        ]
    elif type == 'TRACK':
        return [
            Value('library_key', app.key_num(wrapper.key)),
            Value('name', wrapper.title.replace("'", "%27")),
            Value('name_sort', wrapper.titleSort.replace("'", "%27")),
            Value('artist_key', app.key_num(wrapper.grandparentKey)),
            Value('album_key', app.key_num(wrapper.parentKey)),
            Value('duration', wrapper.duration),
            Value('track_num', wrapper.index),
            Value('disc_num', wrapper.parentIndex),
            Value('download_url', quote(wrapper.downloadURL)),
            Value('bitrate', wrapper.bitrate),
            Value('size', wrapper.size),
            Value('format', wrapper.format)
        ]

    return None


def update_after_refresh(data):
    for entry in data:
        type = entry['type']

        table = {
            'ARTIST': 'artists',
            'ALBUM': 'albums',
            'TRACK': 'tracks'
        }.get(type)

        if entry['deleted']:
            delete(table, Value('library_key', entry['library_key']))
        else:
            media = ph.get_by_key(entry['library_key'])

            if type == 'ARTIST':
                wrapper = ph.ArtistWrapper(media)
            elif type == 'ALBUM':
                wrapper = ph.AlbumWrapper(media)
            elif type == 'TRACK':
                wrapper = ph.TrackWrapper(media)

            info = get_wrapper_information(wrapper, type)
            insert_direct(table, info)


