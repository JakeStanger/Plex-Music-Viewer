import taglib
from plexapi.server import PlexServer
from src.plex_api_extras import get_additional_track_data
import sys
from json import load

# Load settings
settings = load(open('settings.json'))

if settings['backends']['plex']['server_token']:
    plex = PlexServer(settings['backends']['plex']['server_address'], settings['backends']['plex']['server_token'])
    music = plex.library.section(settings['librarySection'])
    settings['musicLibrary'] = music.locations[0]
else:
    print("Setting not set. Exiting...")
    sys.exit()

music = plex.library.section('Music')


artists = music.all()
numArtists = len(artists)
i = 1
for artist in artists:
    print("(" + str(i) + "/" + str(numArtists) + ") " + artist.title)
    i += 1

    albums = artist.albums()
    numAlbums = len(albums)
    j = 1
    for album in artist.albums():
        print("-- (" + str(j) + "/" + str(numAlbums) + ") " + album.title)
        j += 1
        for track in album.tracks():
            additional = get_additional_track_data(track.key, settings['backends']['plex']['server_token'])

            song = taglib.File(additional['downloadURL'])

            # Update tags
            song.tags["ALBUM"] = album.title
            song.tags["ARTIST"] = artist.title
            song.tags["DATE"] = str(album.year)
            song.tags["GENRE"] = [genre.tag for genre in album.genres]
            song.tags["TITLE"] = track.title
            song.tags["TRACKNUMBER"] = str(track.index)
            song.tags["DISCNUMBER"] = str(track.parentIndex)

            errors = song.save()
            if len(errors) > 0:
                print(errors)
