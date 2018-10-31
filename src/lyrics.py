import os
import lyricsgenius as genius

from db import Track


def encode_string(string: str) -> str:
    return string.replace(".", "").replace("/", "-")


def get_lyrics_filename(track: Track) -> str:
    return 'lyrics/%s - %s.txt' % (encode_string(track.artist_name),
                                   encode_string(track.name))


def get_song_lyrics(track: Track) -> str:
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


def update_lyrics(track: Track, lyrics: str):
    if not os.path.exists('lyrics'):
        os.makedirs('lyrics')

    filename = get_lyrics_filename(artist_name, track_name)
    with open(filename, 'w') as f:
        f.write(lyrics)
