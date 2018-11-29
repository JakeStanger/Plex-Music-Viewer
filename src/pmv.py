import base64
import datetime
import logging
import sched
import sys
import time
from functools import wraps
from logging import handlers
from multiprocessing import Manager
from os import path, makedirs
from urllib.parse import unquote
from zipfile import ZipFile

from flask import Flask, render_template, send_file, redirect, url_for, flash, request
from flask_login import LoginManager, login_required, login_user, logout_user
from magic import Magic
from musicbrainzngs import musicbrainz
from plexapi.library import Library
from plexapi.server import PlexServer
from simplejson import dumps, load
from werkzeug.local import LocalProxy
from werkzeug.security import check_password_hash, generate_password_hash

import database as db
import defaults
import argparse
from helper import *

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = handlers.RotatingFileHandler('output.log', backupCount=3)  # TODO Allow log rotation to be configured
formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.info("--BEGIN APPLICATION--")
logger.info("Creating Flask object.")

# Flask configuration
app = Flask(__name__)  # TODO Implement logging throughout application

app.url_map.strict_slashes = False

app.jinja_env.globals.update(int=int)
app.jinja_env.globals.update(format_duration=format_duration)
app.jinja_env.globals.update(format_size=format_size)


def get_song_lyrics(track):
    import lyrics
    return lyrics.get_song_lyrics(track)


app.jinja_env.globals.update(lyrics=get_song_lyrics)

manager = Manager()
_update_stack = manager.list()

# def trigger_database_update():
#     cache = db.get_cache()
#     if len(cache) > 0:
#         db.update_after_refresh(cache)
#         db.clear_cache()


# def listen(msg):
#     if msg['type'] == 'timeline':
#         timeline_entry = msg['TimelineEntry'][0]
#
#         # item = ph.get_by_key(timeline_entry['itemID'])
#         # type = ph.Type(timeline_entry['type']).name
#
#         # _update_stack.append({item: type})
#
#         # print(msg)
#
#         state = timeline_entry['metadataState']
#
#         data = {
#             'section_id': timeline_entry['sectionID'],
#             'library_key': timeline_entry['itemID'],
#             'type': ph.Type(timeline_entry['type']),
#             # 'deleted': state == 'deleted',
#         }
#
#         # print(data)
#
#         if data not in _update_stack:
#             _update_stack.append(data)
#
#         print(_update_stack)
#     #
#     #     db.update_after_refresh([data])
#     #
#     #     if 'updatedAt' in timeline_entry:
#     #
#     #
#     elif msg['type'] == 'backgroundProcessingQueue':
#         update_database()
#

# Load settings
try:
    logger.info("Loading settings from file...")
    settings = load(open('/etc/pmv/settings.json'))
    defaults.set_missing_as_default(settings)
except FileNotFoundError:
    logger.info("No settings file found. Creating a new one with default settings.")
    settings = defaults.default_settings
    defaults.write_settings(settings)

# logger.setLevel(settings['log_level'])  # TODO Set log level from settings

logger.debug('Creating database engine')
app.config['SQLALCHEMY_DATABASE_URI'] = settings['database']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init(app)

app.config.update(SECRET_KEY=settings['secret_key'])

if settings['backends']['plex']['server_token']:
    logger.info("Using Plex backend.")
    plex = PlexServer(settings['backends']['plex']['server_address'], settings['backends']['plex']['server_token'])
    music = plex.library.section(settings['backends']['plex']['music_library_section'])
    settings['musicLibrary'] = music.locations[0]

    logger.debug("Starting plex alert listener.")
    # plex.startAlertListener(listen)  # TODO Fix alert listener

# Login manager configuration
logger.debug("Creating login manager.")
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

logger.debug("Setting musicbrainz useragent.")
musicbrainz.set_useragent('Plex Music Viewer', '0.1',
                          'https://github.com/JakeStanger/Plex-Music-Viewer')  # TODO Proper version management


@app.errorhandler(404)
def page_not_found(e, custom_message=None):
    logger.debug("Throwing error 404 (%s)" % custom_message or e)
    return render_template('error.html', code=str(404), message=custom_message or e)


app.jinja_env.globals.update(throw_error=throw_error)


def import_user() -> LocalProxy:
    """
    Imports the current user from Flask and returns it.
    Used outside of requests where current_user is otherwise None.
    :return: The current user.
    """
    try:
        from flask_login import current_user
        return current_user
    except ImportError:
        raise ImportError(
            'Flask-Login.current_user could not be imported.')


def require_permission(permission: db.Permission,
                       get_user_func: LocalProxy = import_user):  # TODO Require login here rather than on all functions
    """
    Decorating a function with this ensures the current
    user has db.Permission to load to page.
    :param permission:
    :param get_user_func:
    :return:
    """

    def permission_wrapper(func):
        @wraps(func)
        def permission_inner(*args, **kwargs):
            user = get_user_func()
            if user.has_permission(permission):
                return func(*args, **kwargs)
            else:
                logger.info('User %s attempted to send request but did not have permission %s.'
                            % (user.username, permission))
                throw_error(401, "Missing permission <b>%s</b>." % permission)

        return permission_inner

    return permission_wrapper


def admin_required(func, get_user=import_user):
    @wraps(func)
    def admin_wrapper(*args, **kwargs):
        user = get_user()
        if not user.is_admin:
            logger.info("User %s attempted to send an admin-only request without admin privileges.")
            throw_error(401, "Only administrators can do this.")

        return func(*args, **kwargs)

    return admin_wrapper


# Support login via API
@login_manager.request_loader
def request_loader(req):
    # Attempt login via URL arg
    api_key = req.args.get('api_key')
    if api_key:
        user = db.get_user_by_api_key(api_key)
        if user:
            return user

    # Attempt login via header parameter
    api_key = req.headers.get('Authorization')
    if api_key:
        api_key = api_key.replace('Basic ', '', 1)
        try:
            api_key = base64.b64decode(api_key)
        except TypeError:
            pass
        user = db.get_user_by_api_key(api_key)
        if user:
            return user

    return None


@app.route('/error')
def error():
    return render_template('error.html', code=str(402), message="You do not have permission to view this page.")


@app.route('/')
def index():
    return redirect(url_for('artist'))


@app.route('/artist')
@app.route("/artist/<int:artist_id>")
@login_required
@require_permission(db.Permission.music_can_view)
def artist(artist_id: int = None):
    if artist_id:
        artist = db.get_artist_by_id(artist_id)
        albums = artist.albums
        albums.sort(key=lambda x: x.release_date or datetime.date(datetime.MINYEAR, 1, 1), reverse=True)

        return render_template('table.html', albums=albums, title=artist.name)
    else:
        artists = db.get_artists()
        artists.sort(key=lambda x: x.name_sort)

        return render_template('table.html', artists=artists, title="Artists")


@app.route("/album/<int:album_id>")
@login_required
@require_permission(db.Permission.music_can_view)
def album(album_id: int):
    album = db.get_album_by_id(album_id)
    tracks = album.tracks
    tracks = sorted(tracks, key=lambda x: (x.disc_num, x.track_num))

    return render_template('table.html', tracks=tracks, title=album.name, key=album.id, parentKey=album.artist_key,
                           parentTitle=album.artist_name, settings=settings, totalSize=album.total_size())


@app.route("/track/<int:track_id>")
@login_required
@require_permission(db.Permission.music_can_view)
def track(track_id: int):
    import images
    import lyrics
    track = db.get_track_by_id(track_id)

    banner_colour = images.get_predominant_colour(track.album)
    text_colour = images.get_text_colour(banner_colour)

    return render_template('track.html', track=track,
                           banner_colour=banner_colour, text_colour=text_colour,
                           lyrics=lyrics.get_song_lyrics(track)
                           .split('\n'))


@app.route("/track_file/<int:track_id>")
@app.route("/track_file/<int:track_id>/<download>")
@login_required
@require_permission(db.Permission.music_can_download)
def track_file(track_id: int, download=False):
    track = db.get_track_by_id(track_id)

    decoded = unquote(track.download_url)

    mime = Magic(mime=True)
    mimetype = mime.from_file(decoded)

    return send_file(decoded, mimetype=mimetype,
                     as_attachment=download, attachment_filename='%s.%s' % (track.name, track.format))


@app.route('/playlists')
@login_required
@require_permission(db.Permission.music_can_view)
def playlists():
    return render_template('playlists.html')


@app.route('/edit_lyrics/<int:track_id>', methods=['POST'])
@login_required
@require_permission(db.Permission.music_can_edit)
def edit_lyrics(track_id: int):
    import lyrics
    current_track = db.get_track_by_id(track_id)

    lyrics.update_lyrics(current_track, request.form.get('lyrics'))

    flash('Lyrics successfully updated', category='success')
    return redirect(url_for('track', track_id=track_id))


@app.route('/edit_metadata/<int:track_id>', methods=['POST'])
@login_required
@require_permission(db.Permission.music_can_edit)
def update_metadata(track_id: int):
    print(request.form)
    return str(track_id)  # TODO Write metadata updating (local, database, plex)


# TODO URGENT - Rewrite search (front + backend)
@app.route("/search", methods=['GET', 'POST'])
@app.route("/search/<query>", methods=['GET', 'POST'])
@login_required
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

    return render_template('table.html', artists=artists, albums=albums, tracks=tracks, title=query,
                           is_search=True, prev=request.referrer)


@login_manager.user_loader
def get_user(username):
    return db.get_user(username)


@app.route("/login", methods=['GET', 'POST'])
def login():
    display_flash = False

    if request.method == 'POST':
        username = request.form.get('username').lower()
        password = request.form.get('password')
        remember = request.form.get('remember') is not None
        user = get_user(username)

        if user:
            if check_password_hash(user.password, password):
                login_user(user, remember)
                return redirect(request.args.get('next') or url_for('index'))
            else:
                flash("Incorrect password", category='error')
                display_flash = True
        else:
            flash("Incorrect username", category='error')
            display_flash = True

    return render_template('accounts.html', title="Log in", force_display=display_flash)


@app.route('/signup', methods=['POST'])
def sign_up():
    username = request.form['username'].lower()
    password = request.form['password']
    remember = request.form.get('remember') is not None

    db.add_user(username, generate_password_hash(password))
    # TODO Add some proper validation, redirecting for signup
    # if len(data) == 0:
    user = get_user(username)
    login_user(user, remember)
    return redirect(url_for('index'))
    # else:
    #   return dumps({'error': str(data[0])})


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')


@app.route('/delete_user/<string:username>', methods=['POST', 'DELETE'])
@login_required
@admin_required
def delete_user(username):
    db.delete_user_by_username(username)
    db.session().commit()

    if request.method == 'POST':
        flash("User '%s' successfully deleted." % username, category='success')
        return redirect(request.referrer)
    else:
        return dumps({'message': 'User %s successfully deleted' % username}) \
               @ app.route('/delete_user_by_id/<int:id>', methods=['POST', 'DELETE'])


@login_required
@admin_required
def delete_user_by_id(key: int, restore=False):
    """
    Marks the user with the given ID as deleted.
    Does not actually delete the user from the database
    so that it is possible to restore them. This also
    allows for hard account suspension.
    :param key: The user ID
    :param restore: If this is set to True, undelete the user.
    :return:
    """
    db.delete_user_by_id(key, restore)

    message = "User with ID %r' successfully %s." % (key, "restored" if restore else 'deleted')
    if request.method == 'POST':
        flash(message, category='success')
        return redirect(request.referrer)
    else:
        return dumps({'message': message})


@login_required
@admin_required
def restore_user_by_id(key: int):
    """
    Alias for :func:`delete_user_by_id<app.delete_user_by_id>`.
    Restore is passed as True.
    """
    delete_user_by_id(key, True)


# TODO URGENT - Rewrite this to be more dynamic - only update given values
@login_required
@admin_required
def edit_user_by_id(key: int):
    form = request.form

    db.edit_user_by_id(key, form)

    db.session().commit()

    message = "User with ID %r' successfully edited." % key
    if request.method == 'POST':
        flash(message, category='success')
        return redirect(request.referrer)
    else:
        return dumps({'message': message})


@app.route('/edit_user', methods=['POST'])
@app.route('/edit_user/<username>', methods=['POST'])
@login_required
@admin_required
def edit_user(username=None):  # TODO Add editing by username
    action = request.form.get('action')
    if action:  # If handling an AJAX request from table
        if action == 'edit':
            edit_user_by_id(request.form.get('id'))

        elif action == 'delete':
            delete_user_by_id(request.form.get('id'))

        elif action == 'restore':
            delete_user_by_id(request.form.get('id'), True)

        return dumps(request.form)


@app.route('/admin')
@login_required
@admin_required
def admin():
    return render_template('admin.html', title="Admin", users=db.get_users())


@app.route('/torrent/<artist_name>/<album_name>', methods=['POST'])
@login_required
@require_permission(db.Permission.music_can_download)
def torrent(artist_name, album_name):
    torrent_path = "torrents/" + artist_name + "/" + album_name + ".torrent"

    return send_file(torrent_path, as_attachment=True, attachment_filename=album_name + '.torrent')


@app.route('/zip/<int:album_id>', methods=['POST'])
@login_required
@require_permission(db.Permission.music_can_download)
def zip(album_id):
    # album = ph.get_album(artist_name, album_name)

    album = db.get_album_by_id(album_id)

    filename = "/etc/pmv/zips/%s/%s.zip" % (album.artist_name, album.name)
    if not path.exists(path.dirname(filename)):
        makedirs(path.dirname(filename))

    if not path.isfile(filename):
        z = ZipFile(filename, 'w')
        for track in album.tracks:
            z.write(unquote(track.download_url))
        z.close()

    return send_file(filename, as_attachment=True, attachment_filename=album.name + '.zip')


@app.route('/image/<int:album_id>')
@app.route('/image/<int:album_id>/<width>')
@app.route('/image/<string:artist_name>/<string:album_name>')
@app.route('/image/<string:artist_name>/<string:album_name>/<int:width>')
# @login_required
# @require_permission(db.PermissionType.MUSIC, db.Permission.VIEW)
def image(album_id: int=None, artist_name: str=None, album_name: str=None, width=None):
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


# def delete_entry(entry):
#     table = db.get_table_for(entry['type'])
#     db.delete(table, condition=db.Value('library_key', entry['library_key']))
#
#
# def process_update_stack(update_stack):  # TODO Fix updating when stack changes size during update
#     # print(update_stack)
#     for entry in update_stack:
#         # print(entry)
#         try:
#             item = ph.get_by_key(entry['library_key'])
#             do_recursive_db_update(ph.wrap(item))
#         except NotFound:
#             delete_entry(entry)
#
#     update_stack[:] = []


# --START OF PROGRAM--
if __name__ == "__main__":
    scheduler = sched.scheduler(time.time)
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--update', action='store_true', help='Update the database and exit')

    args = parser.parse_args()

    if args.update:
        with app.app_context():
            db.init(app)
            if settings['backends']['plex']['enable']:
                db.populate_db_from_plex()
            if settings['backends']['mpd']['enable']:
                db.populate_db_from_mpd()
            sys.exit()

    # def run_process_update_stack(update_stack):
    #     try:
    #         process_update_stack(update_stack)
    #     finally:
    #         scheduler.enter(10, 1, run_process_update_stack, (update_stack,))
    #
    #
    # def run_scheduler(update_stack):
    #     run_process_update_stack(update_stack)
    #     scheduler.run()

    # flask = Process(target=app.run, args=(None, None, debug))
    # db_updater = Process(target=run_scheduler, args=(_update_stack,))

    # flask.start()
    #  db_updater.start()

    # flask.join()
    # db_updater.join()
    app.run(debug=False)

    # db_updater.join()
