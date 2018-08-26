import musicbrainzngs as mb


def search():
    artist = 'king crimson'
    album = 'live in mainz 1974'

    release = mb.search_releases(album, limit=1, artist=artist)['release-list'][0]
    with open ('cover.jpg', 'wb') as f:
        f.write(mb.get_image_front(release['id']))


mb.set_useragent('Plex Music Viewer', '0.1',
                 'https://github.com/JakeStanger/Plex-Music-Viewer')  # TODO Proper version management
search()
