import libtorrent as lt
from plexapi.server import PlexServer
from src.plex_api_extras import get_download_location_post
from json import load
from os import path, makedirs
import sys


# Python's built in commonprefix is broken.
# This is a quick fix for that.
def commonprefix(args, sep='/'):
    return path.commonprefix(args).rpartition(sep)[0]


# Load settings
settings = load(open('settings.json'))

if settings['backends']['plex']['server_token']:
    plex = PlexServer(settings['backends']['plex']['server_address'], settings['backends']['plex']['server_token'])
    music = plex.library.section(settings['backends']['plex']['music_library_section'])
    settings['musicLibrary'] = music.locations[0]
else:
    print("Setting not set. Exiting...")
    sys.exit()


albums = music.albums()
numAlbums = len(albums)
i = 1
for album in albums:
    print("(" + str(i) + "/" + str(numAlbums) + ") " + album.title)
    i += 1

    # Create torrent
    fs = lt.file_storage()

    paths = [get_download_location_post(track.key, settings) for track in album.tracks()]
    albumPath = commonprefix(paths)
    lt.add_files(fs, albumPath)

    t = lt.create_torrent(fs)
    t.add_tracker("udp://192.168.0.19:6969/announce", 0)
    fullPath = "/libraries/Music/" + albumPath.replace("music/", '').rsplit("/", 1)[0]

    try:
        lt.set_piece_hashes(t, fullPath)
    except:
        # Print useful information for debugging
        print(fullPath)
        print(albumPath)
        print(album.title)
        sys.exit()

    torrent = t.generate()

    torrentPath = 'torrents/' + album.parentTitle + '/' + album.title + ".torrent"
    if not path.isdir(path.dirname(torrentPath)):
        makedirs(path.dirname(torrentPath))

    if path.exists(torrentPath):
        torrentPath = torrentPath.replace(album.title, album.title + str(i))

    f = open(torrentPath, "wb")
    f.write(lt.bencode(torrent))
    f.close()
