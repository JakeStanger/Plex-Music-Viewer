import os
from os import path
from timeit import default_timer as timer
from typing import List

import mutagen
from plexapi.audio import Artist as PlexArtist, Album as PlexAlbum, Track as PlexTrack
from plexapi.media import MediaPart, Media

import helper
import mpd_helper
from PersistentMPDClient import PersistentMPDClient
from .db import database
from .models import Album, Artist, Track
from .queries import get_artist_by_plex_key, get_album_by_plex_key, get_track_by_plex_key, get_artist_by_hash, \
    get_album_by_hash, get_track_by_hash

db = database()


def get_formatted_date(date):
    if isinstance(date, int):
        return '%s-01-01' % date
    return date


def base_key(key: str) -> int:
    return int(path.basename(key))


def populate_db_from_plex():
    import pmv

    start_time = timer()

    artists: List[PlexArtist] = pmv.music.all()
    for artist in artists:
        print(artist.title)

        artist_hash = helper.generate_artist_hash(artist.title)
        albums: List[PlexAlbum] = artist.albums()

        artist_query = get_artist_by_hash(artist_hash)
        if not artist_query:
            db.session.add(Artist(name=artist.title,
                                  name_sort=artist.titleSort,
                                  album_count=len(albums),
                                  plex_id=base_key(artist.key),
                                  plex_thumb=base_key(artist.thumb) if artist.thumb else None,
                                  hash=artist_hash))
            artist_query = get_artist_by_hash(artist_hash)
        for album in albums:
            print('┣ ' + album.title)

            tracks: List[PlexTrack] = album.tracks()
            album_hash = helper.generate_album_hash(album.title, artist.title)

            album_query = get_album_by_hash(album_hash)
            if not album_query:
                db.session.add(Album(name=album.title,
                                     name_sort=album.titleSort,
                                     artist_key=artist_query.id,
                                     artist_name=artist.title,
                                     release_date=get_formatted_date(album.year),
                                     genres=','.join([genre.tag for genre in album.genres]),
                                     track_count=len(tracks),
                                     plex_id=base_key(album.key),
                                     plex_thumb=base_key(album.thumb),
                                     hash=album_hash))
                album_query = get_album_by_hash(album_hash)

            for track in tracks:
                print("┃ \t┣ " + track.title)

                track_part: MediaPart = [*track.iterParts()][0]
                track_hash = helper.generate_track_hash(track.title, album.title, artist.title, track_part.file)

                track_query = get_track_by_hash(track_hash)
                if not track_query:
                    media: Media = track.media[0]
                    db.session.add(Track(name=track.title,
                                         name_sort=track.titleSort,
                                         artist_key=artist_query.id,
                                         artist_name=artist.title,
                                         album_key=album_query.id,
                                         album_name=album.title,
                                         duration=track.duration,
                                         track_num=track.index,
                                         disc_num=track.parentIndex,
                                         download_url=track_part.file,  # TODO: Use relative instead of full path
                                         bitrate=media.bitrate,
                                         size=track_part.size,
                                         format=media.audioCodec,
                                         plex_id=base_key(track.key),
                                         hash=track_hash))

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

    settings = pmv.settings['backends']['mpd']

    start_time = timer()

    music_library = pmv.settings['music_library']
    unknown_album = "[Unknown Album]"

    client = PersistentMPDClient(host=settings['hostname'], port=settings['port'])

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
        artist_hash = helper.generate_artist_hash(artist)

        artist_query = get_artist_by_hash(artist_hash)
        if not artist_query:
            db.session.add(Artist(name=artist,
                                  name_sort=helper.get_sort_name(artist),
                                  album_count=len(albums),
                                  hash=artist_hash))
            artist_query = get_artist_by_hash(artist_hash)

        for album in albums:
            print('┣ ' + album)
            album_data = albums[album]
            album_hash = helper.generate_album_hash(album, artist)
            tracks = album_data['songs']

            album_query = get_album_by_hash(album_hash)
            if not album_query:
                genre_list = filter(lambda x: len(x) > 0, album_data['genres'])
                db.session.add(Album(name=album,
                                     name_sort=helper.get_sort_name(album),
                                     artist_key=artist_query.id,
                                     artist_name=artist,
                                     release_date=get_formatted_date(album_data['date']),
                                     genres=','.join([genre for genre in genre_list]),
                                     track_count=len(tracks),
                                     hash=album_hash))
                album_query = get_album_by_hash(album_hash)

            for track in tracks:
                track_title = track['title']
                print("┃ \t┣ " + track_title)

                full_path = music_library + track['file']
                track_hash = helper.generate_track_hash(track_title, album, artist, full_path)

                track_query = get_track_by_hash(track_hash)
                if not track_query:
                    db.session.add(Track(name=track_title,
                                         name_sort=helper.get_sort_name(track_title),
                                         artist_key=artist_query.id,
                                         artist_name=artist,
                                         album_key=album_query.id,
                                         album_name=album,
                                         duration=float(track['duration']) * 1000,  # Store time in ms
                                         track_num=track['track'],
                                         disc_num=track['disc'],
                                         download_url=full_path,  # TODO: (CHECK) Use relative instead of full path
                                         bitrate=mutagen.File(full_path).info.bitrate / 1000,  # Store bitrate in kbps
                                         size=os.path.getsize(full_path),
                                         format=full_path.rpartition('.')[-1].lower(),
                                         hash=track_hash))

    print("\nFinished constructing db.session in %r seconds" % round(timer() - start_time))
    print("Committing db.session.\n")
    db.session.commit()
