import json

import websocket
from enum import Enum
from .queries import get_artist_by_plex_key, get_album_by_plex_key, get_track_by_plex_key, commit
from .populators import add_plex_artist, base_key
from plexapi.audio import Artist as PlexArtist, Album as PlexAlbum, Track as PlexTrack


class PlexNotificationState(Enum):
    created = 0
    reporting_progress = 1
    matching = 2
    downloading_metadata = 3
    processing_metadata = 4
    processed = 5
    deleted = 9


class PlexNotificationType(Enum):
    timeline = "timeline"
    playing = "playing"


class PlexItemType(Enum):
    artist = 8
    album = 9
    track = 10


class PlexListener:
    """
    Websocket client for Plex notifications.
    Listens for data changes and updates the database
    accordingly.
    Will block the current thread, so suggested use is to
    run on its own thread/process.
    """
    def __init__(self):
        print("Started Plex listener")
        self.queue = []
        self._create_socket()

    def _create_socket(self):
        import pmv
        plex_settings = pmv.settings['backends']['plex']
        url = "%s/:/websockets/notifications?X-Plex-Token=%s" % \
              (plex_settings['server_address'].replace('http', 'ws'), plex_settings['server_token'])
        self.ws = websocket.WebSocketApp(url,
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close)
        self.ws.run_forever()

    def on_message(self, message):
        try:
            content = json.loads(message)['NotificationContainer']
            if content['type'] == PlexNotificationType.timeline.value:
                entry = content['TimelineEntry'][0]
                # print(entry)

                state = entry['state']
                if state == PlexNotificationState.processed.value or state == PlexNotificationState.deleted.value:
                    obj = {'id': entry['itemID'], 'state': state, 'type': entry['type']}
                    self.queue.append(obj)

                if ('queueSize' not in entry or entry['queueSize'] == 1) and len(self.queue) > 0:
                    import pmv
                    from helper import generate_artist_hash, generate_album_hash, generate_track_hash
                    print("Processing queue:")
                    print(self.queue)
                    for item in self.queue:
                        key = item['id']
                        state = item['state']
                        if item['type'] == PlexItemType.artist.value:
                            with pmv.app.app_context():
                                artist = get_artist_by_plex_key(key)
                                if state == PlexNotificationState.deleted.value:
                                    if artist:
                                        print("Deleting %s" % artist.name)
                                        artist.delete()
                                else:
                                    plex_artist: PlexArtist = pmv.music.fetchItem('/library/metadata/%s' % key)
                                    if artist:
                                        print("Updating %s" % plex_artist.title)
                                        artist.name = plex_artist.title
                                        artist.name_sort = plex_artist.titleSort
                                        artist.album_count = len(plex_artist.albums())
                                        artist.plex_id = base_key(plex_artist.key)
                                        artist.plex_thumb=base_key(plex_artist.thumb) if plex_artist.thumb else None
                                        artist.hash = generate_artist_hash(plex_artist.title)
                                    else:
                                        print("Creating %s" % plex_artist.title)
                                        add_plex_artist(plex_artist)

                    with pmv.app.app_context():
                        commit()
                    # Empty queue
                    self.queue = []
        except Exception as e:
            print("Error: %s" % e)

    def on_error(self, error):
        print(error)

    def on_close(self):
        print("Socket closed")  # TODO Log

    def close(self):
        self.ws.close()
