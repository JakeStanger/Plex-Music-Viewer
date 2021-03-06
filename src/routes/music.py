import datetime
import operator
from functools import reduce
from urllib.parse import unquote

from flask import render_template, redirect, url_for, Blueprint, send_file, request, flash, make_response
from magic import Magic

import database as db
from helper import get_current_user
from .helpers import require_permission, get_json_response, wants_html

bp = Blueprint('music', __name__, url_prefix='/music')
al = Blueprint('album', __name__, url_prefix='/music/album')
tr = Blueprint('track', __name__, url_prefix='/music/track')
pl = Blueprint('playlist', __name__, url_prefix='/music/playlist')


@bp.route('/artist')
@bp.route("/artist/<int:artist_id>")
@require_permission(db.Permission.music_can_view)
def artist(artist_id: int = None):
    if artist_id:
        artist = db.get_artist_by_id(artist_id)
        albums = artist.albums
        albums.sort(key=lambda x: x.release_date or datetime.date(datetime.MINYEAR, 1, 1), reverse=True)

        if 'text/html' in request.accept_mimetypes:
            return_data = render_template('table.html', albums=albums, title=artist.name)
        else:
            return_data = get_json_response(albums)
    else:
        artists = db.get_artists()
        artists.sort(key=lambda x: x.name_sort)
        if wants_html():
            return_data = render_template('table.html', artists=artists, title="Artists")
        else:
            return_data = get_json_response(artists)
    return return_data


@al.route("/<int:album_id>")
@require_permission(db.Permission.music_can_view)
def album(album_id: int):
    import pmv
    album = db.get_album_by_id(album_id)
    tracks = album.tracks
    tracks = sorted(tracks, key=lambda x: (x.disc_num, x.track_num))

    if wants_html():
        return render_template('table.html', tracks=tracks, title=album.name, key=album.id, parentKey=album.artist_key,
                               parentTitle=album.artist_name, settings=pmv.settings, totalSize=album.total_size())
    else:
        return get_json_response(tracks)


@tr.route("/<int:track_id>")
def track(track_id: int):
    import images
    import lyrics
    track = db.get_track_by_id(track_id)

    playlists = db.get_playlists_by_user(get_current_user())
    # track.album

    banner_colour = images.get_predominant_colour(track.album)
    button_colour = images.get_button_colour(banner_colour)
    text_colour = images.get_text_colour(banner_colour)

    if wants_html():
        return render_template('track.html', track=track,
                               banner_colour=banner_colour, text_colour=text_colour, button_colour=button_colour,
                               lyrics=lyrics.get_song_lyrics(track)
                               .split('\n'), playlists=playlists)
    else:
        return get_json_response(track, max_depth=1)


@tr.route("/<int:track_id>/file")
@tr.route("/<int:track_id>/file/<download>")
@require_permission(db.Permission.music_can_download)
def track_file(track_id: int, download=False):
    import pmv
    track = db.get_track_by_id(track_id)

    file_path = pmv.settings['music_library'] + unquote(track.download_url)

    mime = Magic(mime=True)
    mimetype = mime.from_file(file_path)

    return send_file(file_path, mimetype=mimetype,
                     as_attachment=download, attachment_filename='%s.%s' % (track.name, track.format))


@pl.route('/')
@require_permission(db.Permission.music_can_view)
def playlists():
    playlists = db.get_playlists_by_user(get_current_user()) or []

    if wants_html():
        return render_template('playlists.html', playlists=playlists)
    else:
        return get_json_response(playlists)


@pl.route('/<int:playlist_id>')
@require_permission(db.Permission.music_can_view)
def playlist(playlist_id: int):
    import pmv
    playlist = db.get_playlist_by_id(playlist_id)

    if wants_html():
        return render_template('table.html', tracks=playlist.tracks, title=playlist.name, settings=pmv.settings,
                               is_playlist=True, key=playlist_id,
                               totalSize=reduce(operator.add, [track.size for track in playlist.tracks]))
    else:
        tracks = [*map(lambda x: x.id, playlist.tracks)]
        return get_json_response(playlist, max_depth=1, append={'tracks': tracks})


@pl.route('/add/<string:name>', methods=['POST'])
@require_permission(db.Permission.music_can_view)
def create_playlist(name: str):
    playlist = db.Playlist(name=name, creator_id=get_current_user().id)
    db.add_single(playlist)

    return redirect(request.referrer)


@pl.route('/<int:playlist_id>/add/<int:track_id>', methods=['POST'])
@pl.route('/<int:playlist_id>/add/<int:track_id>/<string:playlist_name>', methods=['POST'])
@pl.route('/add/<int:track_id>', methods=['POST'])
@pl.route('/add/<int:track_id>/<string:playlist_name>', methods=['POST'])
@require_permission(db.Permission.music_can_view)
def add_to_playlist(track_id: int, playlist_id: int = None, playlist_name: str = None):
    if not playlist_id:
        playlist_id = int(request.form.get('playlist_id'))

    if playlist_id == -1:
        if not playlist_name:
            playlist_name = request.form.get('playlist_name')
        playlist = db.Playlist(name=playlist_name, creator_id=get_current_user().id)
    else:
        playlist = db.get_playlist_by_id(playlist_id)

    track = db.get_track_by_id(track_id)

    # Check track not already in playlist
    f = [*filter(lambda track: track.id == track_id, playlist.tracks)]
    if not f or len(f) == 0:
        playlist.tracks.append(track)
        db.session().commit()

    return redirect(request.referrer)


@tr.route('/<int:track_id>/lyrics', methods=['GET', 'POST'])
@require_permission(db.Permission.music_can_edit)
def lyrics(track_id: int):
    import lyrics
    current_track = db.get_track_by_id(track_id)

    if request.method == "POST":
        lyrics.update_lyrics(current_track, request.form.get('lyrics'))

        flash('Lyrics successfully updated', category='success')
        return redirect(url_for('music.track', track_id=track_id))

    lyrics = lyrics.get_song_lyrics(current_track)
    response = make_response(lyrics, 200)
    response.mimetype = "text/plain"
    return response


@tr.route('/<int:track_id>/metadata', methods=['POST'])
@require_permission(db.Permission.music_can_edit)
def update_metadata(track_id: int):
    print(request.form)
    return str(track_id)  # TODO Write metadata updating (local, database, plex)


@bp.route("/search", methods=['GET', 'POST'])
@bp.route("/search/<query>", methods=['GET', 'POST'])
@require_permission(db.Permission.music_can_view)
def search(query=None, for_artists=True, for_albums=True, for_tracks=True):
    if not query:
        query = request.form.get('query')

    if for_artists:
        artists = db.get_artists_by_name(query)

    if for_albums:
        albums = db.get_albums_by_name(query)

    if for_tracks:
        tracks = db.get_tracks_by_name(query)

    if wants_html():
        return render_template('table.html', artists=artists, albums=albums, tracks=tracks, title=query,
                               is_search=True, prev=request.referrer)
    else:
        return get_json_response({'artists': artists, 'albums': albums, 'tracks': tracks}, max_depth=3)
