from plexapi.server import PlexServer
from json import load
from src.pmv import get_album
import sys


# Load settings
settings = load(open('settings.json'))

if settings['serverToken']:
    plex = PlexServer(settings['serverAddress'], settings['serverToken'])
    music = plex.library.section(settings['librarySection'])
    settings['musicLibrary'] = music.locations[0]
else:
    print("Setting not set. Exiting...")
    sys.exit()


album = get_album('King Crimson', "Live In Mainz 1973")
prevDisc = 0
for track in album.tracks():
    if track.parentIndex != prevDisc:
        print("\nDisc " + track.parentIndex)
    print(track.index + ". " + track.title)
    prevDisc = track.parentIndex
