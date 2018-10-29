import os
import lyricsgenius as genius


def encode_string(string: str) -> str:
    return string.replace(".", "").replace("/", "-")


def get_lyrics_filename(artist_name: str, track_name: str) -> str:
    return 'lyrics/%s - %s.txt' % (encode_string(artist_name),
                                   encode_string(track_name))


def get_song_lyrics(artist_name: str, track_name: str) -> str:
    import pmv

    # Remove illegal characters (full stops get interpreted weirdly by lyricsgenius)
    filename = get_lyrics_filename(artist_name, track_name)

    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            return f.read().decode('utf8')

    if pmv.settings['genius_api']:
        g = genius.Genius(pmv.settings['genius_api'])

        try:
            song = g.search_song(track_name, artist_name=artist_name)
        except ConnectionError:
            return 'Failed to reach Genius.'

        if not song:
            return "Lyrics not found."

        if not os.path.exists('lyrics'):
            os.makedirs('lyrics')

        song.save_lyrics(filename, overwrite=True, binary_encoding=True)
        return song.lyrics
    else:
        return 'Genius API key not set.'


def update_lyrics(self, lyrics):
    if not os.path.exists('lyrics'):
        os.makedirs('lyrics')

    filename = self.get_lyrics_filename()
    with open(filename, 'w') as f:
        f.write(lyrics)
