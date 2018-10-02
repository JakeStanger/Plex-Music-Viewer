"""
Used for generating and executing queries when using own database.
"""

from os import path
from urllib.parse import quote

from flaskext.mysql import MySQL
from pymysql import ProgrammingError

from src import app, plex_helper as ph, defaults

mysql = None
_cache = []


def init():
    global mysql
    mysql = MySQL()
    mysql.init_app(app.get_app())


def get_cache():
    return _cache


def insert_into_cache(data: dict):  # TODO Put this into use
    _cache.append(data)


def clear_cache():
    global _cache
    _cache = []


class Value:
    def __init__(self, column, value):
        self.column = column
        self.value = value

    def __repr__(self):
        return "<%s: %s>" % (self.column, self.value)


# def call_proc(proc: str, values):
#     global mysql
#     if not mysql:
#         init()
#
#     conn = mysql.connect()
#     cursor = conn.cursor()
#
#     cursor.callproc('sp_createUser', values)
#
#     data = cursor.fetchall()
#     conn.close()
#
#     return data


def exec_sql(query: str, table: str, fetch_one: bool = False, fetch_all: bool = False, commit: bool = False):
    global mysql
    if not mysql:
        init()

    conn = mysql.connect()
    cursor = conn.cursor()

    try:
        cursor.execute(query)
    except ProgrammingError:
        if table in defaults.default_tables:
            cursor.execute(defaults.default_tables[table])
            cursor.execute(query)

    if commit:
        conn.commit()

    if fetch_one:
        return cursor.fetchone()
    if fetch_all:
        return cursor.fetchall()

    conn.close()


def _generate_where(conditions):
    return " WHERE %s" % ' AND '.join("%s='%s'" % (condition.column, condition.value)
                                      for condition in conditions) if conditions else ''


def _generate_on_duplicate_key_update(columns):
    return " ON DUPLICATE KEY UPDATE %s" % ','.join("%s='%s'" % (column.column, column.value) for column in columns)


def get_one(table: str, columns: list = None, conditions: list = None):
    return exec_sql("SELECT %s FROM %s" % (','.join(col for col in columns) if columns else '*', table)
                    + " WHERE %s" % ' AND '.join("%s='%s'" % (condition.column, condition.value)
                                                 for condition in conditions) if conditions else '', table, fetch_one=True)


def get_all(table: str, columns: list = None, conditions: list = None):
    return exec_sql("SELECT %s FROM %s" % (','.join(col for col in columns) if columns else '*', table)
                    + (" WHERE %s" % ' AND '.join("%s='%s'" % (condition.column, condition.value)
                                                  for condition in conditions) if conditions else ''), table, fetch_all=True)


def insert_direct(table: str, values: list, overwrite=False):
    exec_sql("INSERT INTO %s VALUES (%s) %s" % (table,
                                                ','.join("'%s'" % value.value for value in values),
                                                _generate_on_duplicate_key_update(values) if overwrite else ''),
             table, commit=True)


def insert_specific(table: str, values: list, overwrite=False):
    exec_sql("INSERT %s INTO %s (%s) VALUES (%s)" % (table,
                                                     ','.join(value.column for value in values),
                                                     ','.join('%s' % value.value for value in values),
                                                     _generate_on_duplicate_key_update(values) if overwrite else ''),
             table, commit=True)


def update(table: str, values: list, conditions: list = None):
    exec_sql("UPDATE %s SET %s" % (table, ','.join("%s='%s'" % (value.column, value.value) for value in values))
             + _generate_where(conditions), table, commit=True)


def delete(table: str, condition: Value = None):
    exec_sql("DELETE FROM %s" % table
             + (" WHERE %s='%s'" % (condition.column, condition.value) if condition else ''), table, commit=True)


def get_wrapper_as_values(wrapper, type: ph.Type):
    if type == ph.Type.ARTIST:
        return [
            Value('library_key', app.key_num(wrapper.key)),
            Value('name', quote(wrapper.title)),
            Value('name_sort', quote(wrapper.titleSort)),
            Value('thumb', path.basename(wrapper.thumb) if wrapper.thumb else 0),
            Value('album_count', wrapper.num_albums)
        ]
    elif type == ph.Type.ALBUM:
        return [
            Value('library_key', app.key_num(wrapper.key)),
            Value('name', quote(wrapper.title)),
            Value('name_sort', quote(wrapper.titleSort)),
            Value('artist_key', app.key_num(wrapper.parentKey)),
            Value('artist_name', quote(wrapper.parentTitle)),
            Value('year', wrapper.year),
            Value('genres', ','.join(wrapper.genres)),
            Value('thumb', path.basename(wrapper.thumb) if wrapper.thumb else 0),
            Value('track_count', wrapper.num_tracks),
            Value('total_size', wrapper.total_size)
        ]
    elif type == ph.Type.TRACK:
        return [
            Value('library_key', app.key_num(wrapper.key)),
            Value('name', quote(wrapper.title)),
            Value('name_sort', quote(wrapper.titleSort)),
            Value('artist_key', app.key_num(wrapper.grandparentKey)),
            Value('artist_name', quote(wrapper.grandparentTitle)),
            Value('album_key', app.key_num(wrapper.parentKey)),
            Value('album_name', quote(wrapper.parentTitle)),
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
        type = ph.Type[entry['type']]

        table = {
            ph.Type.ARTIST: 'artists',
            ph.Type.ALBUM: 'albums',
            ph.Type.TRACK: 'tracks'
        }.get(type)

        if entry['deleted']:
            delete(table, Value('library_key', entry['library_key']))
            print("Deleted %s from %s" % (entry['library_key'], table))
        else:
            media = ph.get_by_key(entry['library_key'])

            if type == ph.Type.ARTIST:
                wrapper = ph.ArtistWrapper(media)
            elif type == ph.Type.ALBUM:
                wrapper = ph.AlbumWrapper(media)
            elif type == ph.Type.TRACK:
                wrapper = ph.TrackWrapper(media)

            info = get_wrapper_as_values(wrapper, type)
            insert_direct(table, info, overwrite=True)

            print("Added %s with key %s to table %s" % (wrapper.title, wrapper.key, table))


def get_artists():
    return get_all('artists')


def get_artist_by_key(library_key: int):
    return get_one('artists', conditions=[Value('library_key', library_key)])


def get_artist_by_name(name: str):
    return get_one('artists', conditions=[Value('name', quote(name))])


def update_artist(row):
    update('artists', row, [row[0]])
    print("Updated artist: %s." % row[1])


def get_album_by_key(library_key: int):
    return get_one('albums', conditions=[Value('library_key', library_key)])


def get_albums_for(artist_key: int):
    return get_all('albums', conditions=[Value('artist_key', artist_key)])


def get_album_for(artist_key: int, name: str):
    return get_one('albums', conditions=[Value('artist_key', artist_key), Value('name', quote(name))])


def update_album(row):
    update('albums', row, conditions=[row[0]])
    print("Updated album: %s." % row[1])


def get_track_by_key(library_key: int):
    return get_one('tracks', conditions=[Value('library_key', library_key)])


def get_tracks_for(album_key: int):
    return get_all('tracks', conditions=[Value('album_key', album_key)])


def get_track_for(album_key: int, name: str):
    return get_one('tracks', conditions=[Value('album_key', album_key), Value('name', quote(name))])


def update_track(row):
    update('tracks', row, conditions=[row[0]])
    print("Updated track: %s." % row[1])


def get_table_for(media_type: ph.Type):
    return {
        ph.Type.ARTIST: 'artists',
        ph.Type.ALBUM: 'albums',
        ph.Type.TRACK: 'tracks'

    }.get(media_type)


def create_user(username: str, hashed_password: str,
                music_perms: int, movie_perms: int, tv_perms: int, is_admin: bool = False):
    insert_direct('users',
                  [Value('username', username),
                   Value('password', hashed_password),
                   Value('music_perms', music_perms),
                   Value('movie_perms', movie_perms),
                   Value('tv_perms', tv_perms),
                   Value('is_admin', 1 if is_admin else 0)])

    print("Successfully created user %s" % username)