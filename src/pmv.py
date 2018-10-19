import logging
import sched
import time
from functools import wraps
from logging import handlers
from multiprocessing import Process, Manager
from os import path, symlink, makedirs
from urllib.parse import unquote
from zipfile import ZipFile

from flask import Flask, render_template, send_file, redirect, url_for, flash
from flask_login import LoginManager, login_required, login_user, logout_user
from magic import Magic
from musicbrainzngs import musicbrainz
from plexapi.exceptions import NotFound
from plexapi.library import Library, LibrarySection
from plexapi.server import PlexServer
from simplejson import dumps, load
from werkzeug.local import LocalProxy
from werkzeug.security import generate_password_hash, check_password_hash

import database as db
import db
from db import Permission
import defaults
import images
import plex_helper as ph
from helper import *
from plex_api_extras import get_additional_track_data

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
app.jinja_env.globals.update(get_additional_track_data=get_additional_track_data)

manager = Manager()
_update_stack = manager.list()


def trigger_database_update():
    cache = db.get_cache()
    if len(cache) > 0:
        db.update_after_refresh(cache)
        db.clear_cache()


def listen(msg):
    if msg['type'] == 'timeline':
        timeline_entry = msg['TimelineEntry'][0]

        # item = ph.get_by_key(timeline_entry['itemID'])
        # type = ph.Type(timeline_entry['type']).name

        # _update_stack.append({item: type})

        # print(msg)

        state = timeline_entry['metadataState']

        data = {
            'section_id': timeline_entry['sectionID'],
            'library_key': timeline_entry['itemID'],
            'type': ph.Type(timeline_entry['type']),
            # 'deleted': state == 'deleted',
        }

        # print(data)

        if data not in _update_stack:
            _update_stack.append(data)

        print(_update_stack)
    #
    #     db.update_after_refresh([data])
    #
    #     if 'updatedAt' in timeline_entry:
    #
    #
    elif msg['type'] == 'backgroundProcessingQueue':
        update_database()


# Load settings
try:
    logger.info("Loading settings from file...")
    settings = load(open('settings.json'))
    defaults.set_missing_as_default(settings)
except FileNotFoundError:
    logger.info("No settings file found. Creating a new one with default settings.")
    settings = defaults.default_settings
    defaults.write_settings(settings)

# logger.setLevel(settings['log_level'])  # TODO Set log level from settings

logger.debug("Setting MySQL database settings.")
app.config['MYSQL_DATABASE_USER'] = settings['database']['user']
app.config['MYSQL_DATABASE_PASSWORD'] = settings['database']['password']
app.config['MYSQL_DATABASE_DB'] = settings['database']['database']
app.config['MYSQL_DATABASE_HOST'] = settings['database']['hostname']

app.config.update(SECRET_KEY=settings['secret_key'])

db.init()

if settings['serverToken']:
    logger.info("Using Plex backend.")
    plex = PlexServer(settings['serverAddress'], settings['serverToken'])
    music = plex.library.section(settings['librarySection'])
    settings['musicLibrary'] = music.locations[0]

    logger.debug("Starting plex alert listener.")
    plex.startAlertListener(listen)

# Login manager configuration
logger.debug("Creating login manager.")
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

logger.debug("Setting musicbrainz useragent.")
musicbrainz.set_useragent('Plex Music Viewer', '0.1',
                          'https://github.com/JakeStanger/Plex-Music-Viewer')  # TODO Proper version management


def get_app():
    global app
    return app


def get_settings() -> dict:
    global settings
    return settings


def get_music() -> Library:
    global music
    return music


def key_num(key):
    if not isinstance(key, int):
        return int(path.basename(key))
    else:
        return key


app.jinja_env.globals.update(key_num=key_num)


@app.errorhandler(404)
def page_not_found(e, custom_message=None):
    logger.debug("Throwing error 404 (%s)" % custom_message or e)
    return render_template('error.html', code=str(404), message=custom_message or e)


app.jinja_env.globals.update(throw_error=throw_error)


# @app.before_request
# def break_static():
#     # Let Apache handle requests on these directories
#     if request.endpoint == 'music' or request.endpoint == 'torrents':
#         abort(404)
#     return None


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


def require_permission(permission: Permission,
                       get_user: LocalProxy = import_user):  # TODO Require login here rather than on all functions
    """
    Decorating a function with this ensures the current
    user has permission to load to page.
    :param permission:
    :param permission_type:
    :param get_user:
    :return:
    """

    def permission_wrapper(func):
        @wraps(func)
        def permission_inner(*args, **kwargs):
            user = get_user()
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


def get_users(with_password: bool = False):
    return db.get_all('users',
                      not with_password and ['user_id', 'username', 'music_perms', 'movie_perms', 'tv_perms',
                                             'is_admin'], [db.Value('is_deleted', 0)])


# # Support login via API TODO introduce API keys or something
# @login_manager.request_loader # TODO play with this function
# def request_loader(req):
#     username = req.form.get('username')
#     password = req.form.get('password')
#     #username = 'Test'
#     #password = '1234'
#     print(username)
#     print(password)
#     user = get_user(username)
#     print("THIS IS A REQUEST")
#     print("THIS IS A REQUEST")
#     print(user.username)
#     user.set_authenticated(check_password_hash(user.hashed_password, password))
#     return user


@app.route('/error')
def error():
    return render_template('error.html', code=str(402), message="You do not have permission to view this page.")


@app.route('/')
def index():
    return redirect(url_for('artist'))


@app.route('/artist')
@app.route("/artist/<int:artist_id>")
@login_required
@require_permission(Permission.music_can_view)
def artist(artist_id: int = None):
    if artist_id:
        artist = ph.ArtistWrapper(row=db.get_artist_by_key(artist_id))
        albums = [ph.AlbumWrapper(row=row) for row in db.get_albums_for(artist.key)]
        albums.sort(key=lambda x: x.year, reverse=True)

        return render_template('table.html', albums=albums, title=artist.title)
    else:
        artists = [ph.ArtistWrapper(row=row) for row in db.get_artists()]
        artists.sort(key=lambda x: x.titleSort)

        return render_template('table.html', artists=artists, title="Artists")


@app.route("/album/<int:album_id>")
@login_required
@require_permission(Permission.music_can_view)
def album(album_id: int):
    album = ph.AlbumWrapper(row=db.get_album_by_key(album_id))
    tracks = [ph.TrackWrapper(row=row) for row in db.get_tracks_for(album.key)]
    tracks = sorted(tracks, key=lambda x: (x.parentIndex, x.index))

    return render_template('table.html', tracks=tracks, title=album.title, key=album.key, parentKey=album.parentKey,
                           parentTitle=album.parentTitle, settings=settings, totalSize=album.size_formatted())


@app.route("/track/<int:track_id>")
def track(track_id: int):
    track = ph.TrackWrapper(row=db.get_track_by_key(track_id))
    thumb_id = track.parent().thumb

    banner_colour = images.get_predominant_colour(thumb_id)
    text_colour = images.get_text_colour(banner_colour)

    lyrics = track.lyrics()

    return render_template('track.html', track=track, thumb_id=thumb_id,
                           banner_colour=banner_colour, text_colour=text_colour, lyrics=lyrics.split("\n"))


@app.route("/track_file/<int:track_id>")
@app.route("/track_file/<int:track_id>/<download>")
@login_required
@require_permission(Permission.music_can_view)
def track_file(track_id: int, download=False):
    track = ph.TrackWrapper(row=db.get_track_by_key(track_id))

    decoded = unquote(track.downloadURL)

    mime = Magic(mime=True)
    mimetype = mime.from_file(decoded)

    return send_file(decoded, mimetype=mimetype,
                     as_attachment=download, attachment_filename='%s.%s' % (track.title, track.format))


@app.route('/edit_lyrics/<int:track_id>', methods=['POST'])
@login_required
@require_permission(Permission.music_can_edit)
def edit_lyrics(track_id: int):
    current_track = ph.TrackWrapper(row=db.get_track_by_key(track_id))

    lyrics = request.form.get('lyrics')
    current_track.update_lyrics(lyrics)

    flash('Lyrics successfully updated', category='success')

    return redirect(url_for('track', track_id=track_id))


@app.route('/edit_metadata/<int:track_id>', methods=['POST'])
@login_required
@require_permission(Permission.music_can_edit)
def update_metadata(track_id: int):
    print(request.form)
    return str(track_id)  # TODO Write metadata updating (local, database, plex)


@app.route("/search", methods=['GET', 'POST'])
@app.route("/search/<query>", methods=['GET', 'POST'])
@login_required
@require_permission(Permission.music_can_view)
def search(query=None, for_artists=True, for_albums=True, for_tracks=True):
    if not query:
        query = request.form.get('query')

    if for_artists:
        artists = music.search(query, libtype="artist", maxresults=settings['searchResults']['artistResults'])
        artists = [ph.ArtistWrapper(artist) for artist in artists]

    if for_albums:
        albums = music.search(query, libtype="album", maxresults=settings['searchResults']['albumResults'])
        albums = [ph.AlbumWrapper(album) for album in albums]

    if for_tracks:
        tracks = music.search(query, libtype="track", maxresults=settings['searchResults']['trackResults'])
        tracks = [ph.TrackWrapper(track) for track in tracks]

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

    db.add_single(db.User(username=username, password=generate_password_hash(password)))
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


@app.route('/delete_user_by_name/<username>', methods=['POST', 'DELETE'])
@login_required
@admin_required
def delete_user_by_name(username):
    db.update('users', [db.Value('is_deleted', 1)], [db.Value('LOWER(username)', username.lower())])

    if request.method == 'POST':
        flash("User '%s' successfully deleted." % username, category='success')
        return redirect(request.referrer)
    else:
        return dumps({'message': 'User %s successfully deleted' % username}) \
               @ app.route('/delete_user_by_id/<int:id>', methods=['POST', 'DELETE'])


@login_required
@admin_required
def delete_user_by_id(id: int, restore=False):
    """
    Marks the user with the given ID as deleted.
    Does not actually delete the user from the database
    so that it is possible to restore them. This also
    allows for hard account suspension.
    :param id: The user ID
    :param restore: If this is set to True, undelete the user.
    :return:
    """

    db.update('users', [db.Value('is_deleted', 0 if restore else 1)], [db.Value('user_id', id)])

    message = "User with ID %r' successfully %s." % (id, "restored" if restore else 'deleted')
    if request.method == 'POST':
        flash(message, category='success')
        return redirect(request.referrer)
    else:
        return dumps({'message': message})


@login_required
@admin_required
def restore_user_by_id(id: int):
    """
    Alias for :func:`delete_user_by_id<app.delete_user_by_id>`.
    Restore is passed as True of course.
    """
    delete_user_by_id(id, True)


@login_required
@admin_required
def edit_user_by_id(id: int):
    form = request.form

    db.update('users', [
        db.Value('username', form.get('username')),
        db.Value('music_perms', form.get('music_perms')),
        db.Value('movie_perms', form.get('movie_perms')),
        db.Value('tv_perms', form.get('tv_perms')),
        db.Value('is_admin', form.get('is_admin'))
    ],
              [db.Value('user_id', id)])

    message = "User with ID %r' successfully edited." % id
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
    return render_template('admin.html', title="Admin", users=get_users())


@app.route('/torrent/<artist_name>/<album_name>', methods=['POST'])
@login_required
@require_permission(Permission.music_can_download)
def torrent(artist_name, album_name):
    torrent_path = "torrents/" + artist_name + "/" + album_name + ".torrent"

    return send_file(torrent_path, as_attachment=True, attachment_filename=album_name + '.torrent')


@app.route('/zip/<int:album_id>', methods=['POST'])
@login_required
@require_permission(Permission.music_can_download)
def zip(album_id):
    # album = ph.get_album(artist_name, album_name)
    album = ph.AlbumWrapper(row=db.get_album_by_key(album_id))

    filename = "zips/%s/%s.zip" % (album.parentTitle, album.title)
    if not path.exists(path.dirname(filename)):
        makedirs(path.dirname(filename))

    if not path.isfile(filename):
        z = ZipFile(filename, 'w')
        for track in album.tracks():
            z.write(unquote(track.downloadURL))
        z.close()

    return send_file(filename, as_attachment=True, attachment_filename=album.title + '.zip')


@app.route('/image/<path:thumb_id>')
@app.route('/image/<path:thumb_id>/<width>')
# @login_required
# @require_permission(PermissionType.MUSIC, Permission.VIEW)
def image(thumb_id, width=None):
    return send_file(images.get_image(thumb_id, width), mimetype='image/png')


def get_parents(media, parents):
    parent = media.parent()
    if parent is not None:
        # Add to front so we create nodes in
        # The correct order.
        parents.insert(0, parent)
        get_parents(parent, parents)

    return parents


def do_recursive_db_update(media):
    print("--", media.title, "--")
    if media is None:
        return

    if type(media) == LibrarySection:
        children = media.all()
    else:
        children = media.children()

    if children is not None:
        for child in children:
            print(child.title)

            child_type = ph.Type.get(child)
            data = db.get_wrapper_as_values(child, child_type)
            table = db.get_table_for(child_type)

            if not db.get_one(table, conditions=data):
                parent_nodes = get_parents(child, [])
                print("^^", ', '.join(m.title for m in parent_nodes))

                for node in parent_nodes:
                    parent_type = ph.Type.get(node)
                    parent_table = db.get_table_for(parent_type)
                    if not db.get_one(parent_table, conditions=[db.Value('library_key', key_num(node.key))]):
                        print(node.key)
                        parent_data = db.get_wrapper_as_values(node, parent_type)
                        db.insert_direct(parent_table, parent_data)

                db.insert_direct(table, data, overwrite=True)

    parent = media.parent()
    if parent is not None:
        do_recursive_db_update(parent)


def do_database_update(names: dict = None, deep=False, drop_old=False):
    """
        Scans the Plex server for changes, and writes them
        to the database.

        :param names: A nested dictionary of artists, albums and tracks to update.
        Leave empty to update the entire database.

        :param deep: Scan every artist, album and track. By default the scanner
        only scans objects where the parent has changed, meaning metadata edits
        will not be picked up. New or albums and tracks will be detected.

        :param drop_old: Delete the current contents of the database
        and perform a complete refresh.

        :return: Dictionary of changed media elements
        """
    # Return data
    updated = {}

    if drop_old:
        db.delete('tracks')
        db.delete('albums')
        db.delete('artists')

    if names:
        artists = [ph.get_artist(name) for name in names.keys()]
    else:
        artists = ph.get_artists()

    for artist in artists:
        print(artist.title)
        data = db.get_wrapper_as_values(artist, ph.Type.ARTIST)

        scan_albums = False
        if not db.get_one('artists', conditions=data):
            db.insert_direct('artists', data, overwrite=True)
            updated[artist.title] = {}
            scan_albums = True

        if scan_albums or deep:
            if names:
                albums = [ph.get_album(artist.title, album_name) for album_name in names.get(artist.title).keys()]
            else:
                albums = artist.albums()

            for album in albums:
                print("\t%s" % album.title)
                data = db.get_wrapper_as_values(album, ph.Type.ALBUM)

                scan_tracks = False
                if not db.get_one('albums', conditions=data):
                    db.insert_direct('albums', data, overwrite=True)
                    updated[artist.title][album.title] = []
                    scan_tracks = True

                if scan_tracks or deep:
                    if names:
                        tracks = [ph.get_track(artist.title, album.title, track_name)
                                  for track_name in names.get(artist.title).get(album.title)]
                    else:
                        tracks = album.tracks()

                    for track in tracks:
                        print("\t\t%s" % track.title)
                        data = db.get_wrapper_as_values(track, ph.Type.TRACK)

                        if not db.get_one('tracks', conditions=data):
                            db.insert_direct('tracks', data, overwrite=True)
                            updated[artist.title][album.title].append(track.title)

    return dumps(updated)


@app.route('/update_database/<int:deep>/<int:drop_old>', methods=['POST'])
@app.route('/update_database/<int:deep>', methods=['POST'])
@app.route('/update_database', methods=['POST'])
@login_required
@admin_required
def update_database(names: dict = None, deep=0, drop_old=0):
    return do_database_update(names, deep == 1, drop_old == 1)


# TODO Tidy function
@app.route('/updateSettings', methods=['POST'])
@admin_required
def setup():
    """
    Writes to the settings.json file with the
    request form data. Also updates global settings
    and Plex instances.
    If settings are already set, or the request succeeds, the user
    is forwarded to index.html.
    If there is an invalid setting, the user is returned to setup.html
    with a relevant message.
    It will also attempt to create a symlink to the music library.
    :return: Either index.html or setup.html depending on conditions.
    """
    global settings
    global plex
    global music

    # If settings already set, do not allow overriding
    if settings['serverToken']:
        return render_template("index.html")

    # Validate inputs and return to setup if any are invalid
    try:
        tmp = PlexServer(request.form['serverAddress'], request.form['serverToken'])
        plex = tmp
    except:
        return render_template("setup.html", msg="Please check your address and/or token.")

    try:
        tmp = plex.library.section(request.form['librarySection'])
        music = tmp
    except:
        return render_template("setup.html", msg="Please check your library section.")

    # Update settings
    settings['serverAddress'] = request.form['serverAddress']
    settings['serverToken'] = request.form['serverToken']
    settings['interfaceToken'] = request.form['interfaceToken']
    settings['librarySection'] = request.form['librarySection']
    settings['searchResults'] = {"artistResults": int(request.form['artistResults']),
                                 "albumResults": int(request.form['albumResults']),
                                 "trackResults": int(request.form['trackResults'])}

    # Write new settings
    with open('../settings.json', 'w') as f:
        f.write(dumps(settings, indent=4))

    settings['musicLibrary'] = music.locations[0]

    # Create symlink to music library
    try:
        if not path.islink('music'):
            symlink(settings['musicLibrary'], 'music')
    except:
        return render_template("setup.html", msg="An error occurred creating a symlink to your music library."
                                                 "Please check your web server file permissions.")

    return render_template('index.html')


def delete_entry(entry):
    table = db.get_table_for(entry['type'])
    db.delete(table, condition=db.Value('library_key', entry['library_key']))


def process_update_stack(update_stack):  # TODO Fix updating when stack changes size during update
    # print(update_stack)
    for entry in update_stack:
        # print(entry)
        try:
            item = ph.get_by_key(entry['library_key'])
            do_recursive_db_update(ph.wrap(item))
        except NotFound:
            delete_entry(entry)

    update_stack[:] = []


# --START OF PROGRAM--
if __name__ == "__main__":
    scheduler = sched.scheduler(time.time)


    def run_process_update_stack(update_stack):
        try:
            process_update_stack(update_stack)
        finally:
            scheduler.enter(10, 1, run_process_update_stack, (update_stack,))


    def run_scheduler(update_stack):
        run_process_update_stack(update_stack)
        scheduler.run()


    # flask = Process(target=app.run, args=(None, None, debug))
    db_updater = Process(target=run_scheduler, args=(_update_stack,))

    # flask.start()
    db_updater.start()

    # flask.join()
    # db_updater.join()
    app.run()

    db_updater.join()