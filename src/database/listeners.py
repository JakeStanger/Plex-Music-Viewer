import json

import websocket
from enum import Enum


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


class PlexListener:
    """
    Websocket client for Plex notifications. python-plexapi does have
    one of these but for whatever reason it does not appear to work.
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
        content = json.loads(message)['NotificationContainer']
        if content['type'] == PlexNotificationType.timeline.value:
            entry = content['TimelineEntry'][0]

            state = entry['state']
            if state == PlexNotificationState.processed.value or state == PlexNotificationState.deleted.value:
                obj = {'id': entry['itemID'], 'state': state}
                print(obj)
                self.queue.append(obj)

            if ('queueSize' not in entry or entry['queueSize'] == 1) and len(self.queue) > 0:
                print("===QUEUE===")
                print(self.queue)
                # TODO Do queue stuff
                self.queue = []

    def on_error(self, error):
        print(error)

    def on_close(self):
        print("Socket closed")  # TODO Log

    def close(self):
        self.ws.close()
