from os import makedirs, path
from urllib.parse import unquote
from zipfile import ZipFile

from flask import Blueprint, send_file

# from pmv import settings
import database as db
from .helpers import require_permission
from .music import bp as ms, pl, al
from json import dumps

bp = Blueprint('media', __name__)


# TODO: Scrap or rework big-time
@bp.route('/torrent/<artist_name>/<album_name>', methods=['POST'])
@require_permission(db.Permission.music_can_download)
def torrent(artist_name, album_name):
    torrent_path = "torrents/" + artist_name + "/" + album_name + ".torrent"

    return send_file(torrent_path, as_attachment=True, attachment_filename=album_name + '.torrent')


@al.route('/<int:album_id>/zip', methods=['POST'])
@al.route('/<int:album_id>/zip/<int:disc>', methods=['POST'])
@pl.route('/<int:playlist_id>/zip/', methods=['POST'])
@require_permission(db.Permission.music_can_download)
def zip(album_id: int = None, playlist_id: int = None, disc: int = None):
    import pmv
    if album_id:
        item = db.get_album_by_id(album_id)
        if disc:
            tracks = db.get_album_disc_by_id(album_id, disc)
            filename = "/etc/pmv/zips/%s/%s-%r.zip" % (item.artist_name, item.name, disc)
        else:
            tracks = item.tracks
            filename = "/etc/pmv/zips/%s/%s.zip" % (item.artist_name, item.name)
    else:
        item = db.get_playlist_by_id(playlist_id)
        tracks = item.tracks
        filename = "/etc/pmv/zips/playlists/%s/%s.zip" % (item.creator, item.name)

    if not path.exists(path.dirname(filename)):
        makedirs(path.dirname(filename))

    if not path.isfile(filename) or playlist_id:
        z = ZipFile(filename, 'w')
        for track in tracks:
            z.write(pmv.settings['music_library'] + unquote(track.download_url), arcname=unquote(track.download_url))
        z.close()

    return send_file(filename, as_attachment=True, attachment_filename='%s%s.zip'
                                                                       % (item.name,
                                                                          '-%s' % disc if disc else ''))


@al.route('/<int:album_id>/image')
@al.route('/<int:album_id>/image/<int:width>')
@ms.route('/image/<string:artist_name>/<string:album_name>')
@ms.route('/image/<string:artist_name>/<string:album_name>/<int:width>')
# @login_required
# @require_permission(db.PermissionType.MUSIC, db.Permission.VIEW)
def image(album_id: int = None, artist_name: str = None, album_name: str = None, width: int = None):
    import images
    if artist_name and album_name:
        album = db.get_album_by_name(artist_name, album_name)
    else:
        album = db.get_album_by_id(album_id)

    if not album:
        album = db.Album(name=album_name, artist_name=artist_name)
    image = images.get_image(album, width)
    if image:
        return send_file(image, mimetype='image/png')
    else:
        return dumps({"message": "No album art could be found for the given artist and album name."})
