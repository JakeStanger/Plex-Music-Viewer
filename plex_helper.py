import math
from enum import Enum
from json import dumps

import app
import database as db
from plex_api_extras import get_additional_track_data
from plexapi.audio import Artist, Album, Track
from urllib.parse import unquote


class ArtistWrapper:
    def __init__(self, artist: Artist=None, row: list=None):
        if not (artist or list):
            raise ValueError("Must pass an artist or database row")

        if artist:
            self._artist = artist
            self.title = artist.title
            self.titleSort = artist.titleSort
            self.key = artist.key
            self.thumb = artist.thumb
            self.num_albums = len(self._artist.albums())
        else:
            self.key = row[0]
            self.title = unquote(row[1])
            self.titleSort = unquote(row[2])
            self.thumb = row[3]
            self.num_albums = row[4]

    def album(self, album_name):
        if self._artist:
            return self._artist.album(album_name)

        return db.get_album_for(self.key, album_name)

    def albums(self):
        if self._artist:
            return [AlbumWrapper(album) for album in self._artist.albums()]

        return [AlbumWrapper(row=row) for row in db.get_albums_for(self.key)]


class AlbumWrapper:
    def __init__(self, album: Album=None, row: list=None):
        if not (album or list):
            raise ValueError("Must pass an album or database row")

        if album:
            self._album = album
            self.title = album.title
            self.titleSort = album.titleSort
            self.key = album.key
            self.parentKey = album.parentKey
            self.parentTitle = album.parentTitle
            self.thumb = album.thumb
            self.genres = [genre.tag for genre in album.genres]
            self.num_tracks = len(self._album.tracks())
            self.artist = album.parentTitle
            self.year = album.year
            self.total_size = sum(track.size for track in self.tracks())
        else:
            self.key = row[0]
            self.title = unquote(row[1])
            self.titleSort = unquote(row[2])
            self.parentKey = row[3]
            self.parentTitle = unquote(row[4])
            self.year = row[5]
            self.genres = row[6].split(',')
            self.thumb = row[7]
            self.num_tracks = row[8]
            self.total_size = row[9]

    def track(self, track_name):
        if self._album:
            return self._album.track(track_name)

        return db.get_track_for(self.key, track_name)

    def tracks(self):
        if self._album:
            return [TrackWrapper(track) for track in self._album.tracks()]

        return [TrackWrapper(row=row) for row in db.get_tracks_for(self.key)]

    def size_formatted(self):
        sizes = ['B', 'kiB', 'MiB', 'GiB', 'TiB']
        if self.total_size == 0:
            return '0B'

        i = int(math.floor(math.log(self.total_size) / math.log(1024)))
        return ('%.3g' % (self.total_size / math.pow(1024, i))) + ' ' + sizes[i]

    def __repr__(self):
        return "<%s>" % self.title


class TrackWrapper:
    def __init__(self, track: Track=None, row: list=None):
        if not (track or list):
            raise ValueError("Must pass a track or database row")

        if track:
            additional = get_additional_track_data(track.key, app.get_settings())

            self._track = track
            self.title = track.title
            self.titleSort = track.titleSort
            self.key = track.key
            self.parentKey = track.parentKey
            self.grandparentKey = track.grandparentKey
            self.grandparentTitle = track.grandparentTitle
            self.parentTitle = track.parentTitle
            self.duration = track.duration
            self.index = track.index
            self.parentIndex = track.parentIndex
            self.downloadURL = additional['downloadURL']
            self.bitrate = additional['bitrate']
            self.size = additional['size']
            self.format = additional['codec']
        else:
            self.key = row[0]
            self.title = unquote(row[1])
            self.titleSort = unquote(row[2])
            self.grandparentKey = row[3]
            self.grandparentTitle = unquote(row[4])
            self.parentKey = row[5]
            self.parentTitle = unquote(row[6])
            self.duration = row[7]
            self.index = row[8]
            self.parentIndex = row[9]
            self.downloadURL = row[10]
            self.bitrate = row[11]
            self.size = row[12]
            self.format = row[13]

    def duration_formatted(self):
        minutes = math.floor(self.duration / 60000)
        seconds = math.floor((self.duration % 60000) / 1000)
        return str(minutes) + ":" + ('0' if seconds < 10 else '') + str(seconds)

    def size_formatted(self):
        sizes = ['B', 'kiB', 'MiB', 'GiB', 'TiB']
        if self.size == 0:
            return '0B'

        i = int(math.floor(math.log(self.size) / math.log(1024)))
        return ('%.3g' % (self.size / math.pow(1024, i))) + ' ' + sizes[i]


# def get_artists():
#     pool = Pool(4)
#     return [*pool.map(TrackWrapper, app.get_music().all())]


def get_artist(artist_name:str=None):
    """
    :param artist_name: An artist name
    :return: The artist
    """
    results = app.get_music().search(artist_name)

    for result in results:
        if result.title == artist_name:
            return result
    if len(results) > 0:
        return ArtistWrapper(results[0])
    return None


def get_album(artist_name, album_name):
    """
    :param artist_name: An artist name
    :param album_name: An album name
    :return: The album
    """
    artist = get_artist(artist_name)
    if artist is not None:
        try:
            album = artist.album(album_name)
            if album is not None:
                return AlbumWrapper(album)
        except:
            return None
    return None


def get_track(artist_name, album_name, track_name):
    """
    :param artist_name: An artist name
    :param album_name: An album name
    :param track_name: A track name
    :return: The track
    """
    album = get_album(artist_name, album_name)
    if album is not None:
        # try:
        track = album.track(track_name)

        if track is not None:
            return TrackWrapper(track)
        # except:
        #     return None
    return None


def get_by_key(key: int):
    return app.get_music().fetchItem('/library/metadata/%r' % key)


def get_artist_json(artists):
    print(artists)
    """
    :param artists: A list of artists
    :return: A JSON string containing data for each artist
    """
    artistList = []
    for artist in artists:
        artistList.append({
            'title': artist.title,
            'titleSort': artist.titleSort,
            'key': artist.key,
            'thumb': artist.thumb,
            'albumCount': len(artist.albums())
        })
    return dumps(artistList)


def get_album_json(albums):
    """
    :param albums: A list of albums
    :return: A JSON string containing data for each album
    """
    albumList = []
    for album in albums:
        albumList.append({
            'title': album.title,
            'titleSort': album.titleSort,
            'key': album.key,
            'thumb': album.thumb,
            'genres': [genre.tag for genre in album.genres],
            'trackCount': len(album.tracks()),
            'artist': album.parentTitle,
            'year': album.year
        })
    return dumps(albumList)


def get_track_json(tracks):
    """
    :param tracks: A list of tracks
    :return: A JSON string containing data for each track
    """
    trackList = []
    for track in tracks:
        additional = get_additional_track_data(track.key, app.get_settings())
        trackList.append({
            'title': track.title,
            'titleSort': track.titleSort,
            'key': track.key,
            'downloadURL': additional['downloadURL'],
            'artist': track.grandparentTitle,
            'album': track.parentTitle,
            'duration_formatted': track.duration_formatted,
            'bitrate': additional['bitrate'],
            'size_formatted': additional['size_formatted'],
            'format': additional['codec'],
            'index': track.index
        })
    return dumps(trackList)


class Type(Enum):
    TRACK = 10
    ALBUM = 9
    ARTIST = 8
