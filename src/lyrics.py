import os
import lyricsgenius as genius
import db


def encode_string(string: str) -> str:
    return string.replace(".", "").replace("/", "-")


def get_lyrics_filename(track: db.Track) -> str:
    return 'lyrics/%s - %s.txt' % (encode_string(track.artist_name),
                                   encode_string(track.name))


def get_song_lyrics(track: db.Track) -> str:
    import pmv

    # Remove illegal characters (full stops get interpreted weirdly by lyricsgenius)
    filename = get_lyrics_filename(track)

    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            return f.read().decode('utf8')

    if pmv.settings['genius_api']:
        g = genius.Genius(pmv.settings['genius_api'])

        try:
            song = g.search_song(track.name, artist_name=track.artist_name)
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


def update_lyrics(track: db.Track, lyrics: str):
    if not os.path.exists('lyrics'):
        os.makedirs('lyrics')

    filename = get_lyrics_filename(track)
    with open(filename, 'w') as f:
        f.write(lyrics)
