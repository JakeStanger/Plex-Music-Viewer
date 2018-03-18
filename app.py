from functools import wraps
from io import BytesIO
from os import path, symlink, makedirs, environ
from timeit import default_timer as timer
from urllib.request import urlopen, quote
from zipfile import ZipFile

from PIL import Image
from flask import Flask, render_template, send_file, redirect, url_for, flash
from flask_login import LoginManager, login_required, login_user, logout_user
from plexapi.library import Library

from plexapi.server import PlexServer
from simplejson import dumps, load
from werkzeug.security import generate_password_hash, check_password_hash

import database as db
import plex_helper as ph
from accounts import User, Permission, PermissionType
from helper import *
from plex_api_extras import getDownloadLocationPOST, get_additional_track_data

# Flask configuration
app = Flask(__name__)

app.url_map.strict_slashes = False

app.jinja_env.globals.update(int=int)
app.jinja_env.globals.update(get_additional_track_data=get_additional_track_data)


def trigger_database_update():
    cache = db.get_cache()
    if len(cache) > 0:
        db.update_after_refresh(cache)
        db.clear_cache()


def listen(msg):

    if msg['type'] == 'timeline':
        timeline_entry = msg['TimelineEntry'][0]

        state = timeline_entry['metadataState']
        if state != 'created' and state != 'deleted':
            return

        data = {
            'section_id': timeline_entry['sectionID'],
            'library_key': timeline_entry['itemID'],
            'type': ph.Type(timeline_entry['type']).name,
            'deleted': state == 'deleted'
        }

        # Avoid duplicates
        for entry in db.get_cache():
            if entry['library_key'] == data['library_key'] and entry['section_id'] == data['section_id']:
                return

        db.insert_into_cache(data)

    if msg['type'] == 'backgroundProcessingQueue':
        trigger_database_update()


# @app.before_request
# def return_cached():
#     if not request.values:
#         response = cache.get(request.path)
#         if response:
#             return response
#
#
# @app.after_request
# def cache_response(response):
#     if not request.values:
#         try:
#             cache.set(request.path, response, CACHE_TIMEOUT)
#         except TypeError:
#             pass
#     return response


# Login manager configuration
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Load settings
settings = load(open('settings.json'))

if settings['serverToken']:
    plex = PlexServer(settings['serverAddress'], settings['serverToken'])
    music = plex.library.section(settings['librarySection'])
    settings['musicLibrary'] = music.locations[0]

    app.config['MYSQL_DATABASE_USER'] = settings['database']['user']
    app.config['MYSQL_DATABASE_PASSWORD'] = settings['database']['password']
    app.config['MYSQL_DATABASE_DB'] = settings['database']['database']
    app.config['MYSQL_DATABASE_HOST'] = settings['database']['hostname']

    app.config.update(SECRET_KEY=settings['secret_key'])

    plex.startAlertListener(listen)


def get_app():
    global app
    return app


def get_settings():
    global settings
    return settings


def get_music() -> Library:
    global music
    return music


def key_num(key):
    return path.basename(key)


@app.errorhandler(404)
def page_not_found(e, custom_message=None):
    return render_template('error.html', code=str(404), message=custom_message or e)


app.jinja_env.globals.update(throw_error=throw_error)


@app.before_request
def break_static():
    # Let Apache handle requests on these directories
    if request.endpoint == 'music' or request.endpoint == 'torrents':
        abort(404)
    return None


def import_user():
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
            'User argument not passed and Flask-Login current_user could not be imported.')


def require_permission(permission_type: PermissionType, permission: Permission, get_user=import_user):
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
            if user.has_permission(permission_type, permission):
                return func(*args, **kwargs)
            else:
                throw_error(401, "Missing permission <b>%s</b> in <b>%s</b>." % (permission, permission_type))

        return permission_inner

    return permission_wrapper


def admin_required(func, get_user=import_user):
    @wraps(func)
    def admin_wrapper(*args, **kwargs):
        user = get_user()
        if not user.is_admin:
            throw_error(401, "Only administrators can do this.")

        return func(*args, **kwargs)

    return admin_wrapper


def get_users(with_password=False):
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
@app.route("/artist/<artist_name>")
@login_required
@require_permission(PermissionType.MUSIC, Permission.VIEW)
def artist(artist_name=None):
    if artist_name:
        # artist = ph.get_artist_by_key(artist_name)
        # return render_template('table.html', albums=artist.albums(), title=artist.title)

        artist = ph.ArtistWrapper(row=db.get_artist_by_name(artist_name))
        albums = [ph.AlbumWrapper(row=row) for row in db.get_albums_for(artist.key)]
        albums.sort(key=lambda x: x.year, reverse=True)

        return render_template('table.html', albums=albums, title=artist.title)
    else:
        artists = [ph.ArtistWrapper(row=row) for row in db.get_artists()]
        artists.sort(key=lambda x: x.titleSort)

        return render_template('table.html', artists=artists, title="Artists")


@app.route("/artist/<artist_name>/<album_name>")
@login_required
@require_permission(PermissionType.MUSIC, Permission.VIEW)
def album(artist_name, album_name):
    artist = ph.ArtistWrapper(row=db.get_artist_by_name(artist_name))
    album = ph.AlbumWrapper(row=db.get_album_for(artist.key, album_name))
    tracks = [ph.TrackWrapper(row=row) for row in db.get_tracks_for(album.key)]

    return render_template('table.html', tracks=tracks, title=album.title,
                           parentTitle=album.parentTitle, settings=settings, totalSize=album.size_formatted())


@app.route("/artist/<artist_name>/<album_name>/<track_name>")
@app.route("/artist/<artist_name>/<album_name>/<track_name>/<download>")
@login_required
@require_permission(PermissionType.MUSIC, Permission.VIEW)
def track(artist_name, album_name, track_name, download=False):
    track = ph.get_track(artist_name, album_name, track_name)

    if download:
        return send_file(track.downloadURL, mimetype="audio",
                         as_attachment=True, attachment_filename='%s.%s' % (track_name, track.format))
    else:
        return redirect(track.downloadURL)


@app.route("/search", methods=['GET', 'POST'])
@app.route("/search/<query>", methods=['GET', 'POST'])
@login_required
@require_permission(PermissionType.MUSIC, Permission.VIEW)
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
def get_user(user):
    row = db.get_one('users',
                     conditions=[db.Value('LOWER(username)', user.lower())])

    if row:
        return User(row[0], row[1], row[2], row[3], row[4], row[5], row[6])
    else:
        return None


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') is not None
        user = get_user(username)
        if user:
            if check_password_hash(user.hashed_password, password):
                login_user(user, remember)
                return redirect(request.args.get('next') or url_for('index'))
            else:
                return "Incorrect password"
        else:
            return "Incorrect username"

    else:  # Display page on GET request
        return render_template('accounts.html', title="Log in")


@app.route('/signup', methods=['POST'])
def sign_up():
    username = request.form['username']
    password = request.form['password']
    remember = request.form.get('remember') is not None

    hashed_password = generate_password_hash(password)

    data = db.call_proc('sp_createUser', (username, hashed_password, 0, 0, 0, 0))

    if len(data) == 0:

        user = get_user(username)
        login_user(user, remember)
        return redirect(url_for('index'))
    else:
        return dumps({'error': str(data[0])})


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/delete_user_by_name/<username>', methods=['POST', 'DELETE'])
@login_required
@admin_required
def delete_user_by_name(username):
    db.update('users', [db.Value('is_deleted', 1)], db.Value('LOWER(username)', username.lower()))

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

    db.update('users', [db.Value('is_deleted', 0 if restore else 1)], db.Value('user_id', id))

    message = "User with ID %r' successfully %s." % (id, "restored" if restore else 'deleted')
    if request.method == 'POST':
        flash(message, category='success')
        return redirect(request.referrer)
    else:
        return dumps({'message': message})


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
              db.Value('user_id', id))

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
@require_permission(PermissionType.MUSIC, Permission.DOWNLOAD)
def torrent(artist_name, album_name):
    torrent_path = "torrents/" + artist_name + "/" + album_name + ".torrent"

    return send_file(torrent_path, as_attachment=True, attachment_filename=album_name + '.torrent')


@app.route('/zip/<artist_name>/<album_name>', methods=['POST'])
@login_required
@require_permission(PermissionType.MUSIC, Permission.DOWNLOAD)
def zip(artist_name, album_name):
    album = ph.get_album(artist_name, album_name)

    filename = "zips/%s/%s.zip" % (artist_name, album_name)
    if not path.exists(path.dirname(filename)):
        makedirs(path.dirname(filename))

    if not path.isfile(filename):
        z = ZipFile(filename, 'w')
        for track in album.tracks():
            z.write(getDownloadLocationPOST(track.key, settings))
        z.close()

    return send_file(filename, as_attachment=True, attachment_filename=album_name + '.zip')


@app.route('/image/<path:thumb_id>')
@app.route('/image/<path:thumb_id>/<width>')
# @login_required
# @require_permission(PermissionType.MUSIC, Permission.VIEW)
def image(thumb_id, width=None):
    """
    Returns the image for the given thumb-id. It is important to
    note that the thumb-id has the initial slash truncated.
    :param thumb_id:
    :param width:
    :return:
    """
    thumb_id = '/' + thumb_id
    url = settings['serverAddress'] + thumb_id + "?X-Plex-Token=" + settings['serverToken']

    try:
        file = BytesIO(urlopen(url).read())
        image = Image.open(file)

        if width:
            size = int(width), int(width)
            image.thumbnail(size, Image.ANTIALIAS)

        tmp_image = BytesIO()
        image.save(tmp_image, 'PNG', quality=90)
        tmp_image.seek(0)

        return send_file(tmp_image, mimetype='image/png')
    except:
        throw_error(400, "invalid thumb-id")


@app.route('/update_database', methods=['POST'])
@login_required
@admin_required
def update_database():
    # Return data
    updated = {
        'artists': [],
        'albums': [],
        'tracks': []
    }

    # artists = [ph.ArtistWrapper(artist) for artist in music.all()]
    artists = music.all()
    num_artists = len(artists)
    i = 1
    for a in artists:
        artist = ph.ArtistWrapper(a)

        print("(%r/%r): %s" % (i, num_artists, artist.title))
        i += 1

        albums = artist.albums()
        num_albums = len(albums)
        artist_values = [
            db.Value('library_key', key_num(artist.key)),
            db.Value('name', artist.title.replace("'", "%27")),
            db.Value('name_sort', artist.titleSort.replace("'", "%27")),
            db.Value('thumb', path.basename(artist.thumb) if artist.thumb else 0),
            db.Value('album_count', num_albums)
        ]

        if not db.get_one('artists', conditions=artist_values):
            db.insert_direct('artists', artist_values, overwrite=True)
            updated['artists'].append(artist.title)

        j = 1
        for album in albums:
            print("\t(%r/%r): %s" % (j, num_albums, album.title))
            j += 1

            tracks = album.tracks()
            num_tracks = len(tracks)

            album_values = [
                db.Value('library_key', key_num(album.key)),
                db.Value('name', album.title.replace("'", "%27")),
                db.Value('name_sort', album.titleSort.replace("'", "%27")),
                db.Value('artist_key', key_num(artist.key)),
                db.Value('artist_name', artist.title.replace("'", "%27")),
                db.Value('year', album.year),
                db.Value('genres', ','.join(album.genres)),
                db.Value('thumb', path.basename(album.thumb) if album.thumb else 0),
                db.Value('track_count', num_tracks),
                db.Value('total_size', sum(track.size for track in tracks))
            ]

            if not db.get_one('albums', conditions=album_values):
                db.insert_direct('albums', album_values, overwrite=True)
                updated['albums'].append(album.title)

            k = 1
            for track in tracks:
                print("\t\t(%r/%r): %s" % (k, num_tracks, track.title))
                k += 1

                track_values = [
                    db.Value('library_key', key_num(track.key)),
                    db.Value('name', track.title.replace("'", "%27")),
                    db.Value('name_sort', track.titleSort.replace("'", "%27")),
                    db.Value('artist_key', key_num(artist.key)),
                    db.Value('artist_name', artist.title.replace("'", "%27")),
                    db.Value('album_key', key_num(album.key)),
                    db.Value('album_name', album.title.replace("'", "%27")),
                    db.Value('duration', track.duration),
                    db.Value('track_num', track.index),
                    db.Value('disc_num', track.parentIndex),
                    db.Value('download_url', quote(track.downloadURL)),
                    db.Value('bitrate', track.bitrate),
                    db.Value('size', track.size),
                    db.Value('format', track.format)
                ]

                if not db.get_one('tracks', conditions=track_values):
                    db.insert_direct('tracks', track_values, overwrite=True)
                    updated['tracks'].append(track.title)

    return dumps(updated)


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
    with open('settings.json', 'w') as f:
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


# --START OF PROGRAM--
if __name__ == "__main__":
    app.run(debug=True)
