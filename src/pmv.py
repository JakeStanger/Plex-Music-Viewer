import argparse
import logging
import sched
import sys
import time
# try:
#     import thread
# except ImportError:
#     import _thread as thread
from threading import Thread
from logging import handlers
from multiprocessing import Manager

from flask import Flask, render_template
from flask_login import LoginManager
from musicbrainzngs import musicbrainz
from plexapi.server import PlexServer
from simplejson import load

import defaults
import routes
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

# Register blueprints
app.register_blueprint(routes.main.bp)
app.register_blueprint(routes.users.bp)

app.register_blueprint(routes.music.bp)
app.register_blueprint(routes.music.al)
app.register_blueprint(routes.music.tr)
app.register_blueprint(routes.music.pl)

app.register_blueprint(routes.media.bp)

app.url_map.strict_slashes = False

# Register functions required inside jinja
app.jinja_env.globals.update(int=int)
app.jinja_env.globals.update(format_duration=format_duration)
app.jinja_env.globals.update(format_size=format_size)


def get_song_lyrics(track):
    import lyrics
    return lyrics.get_song_lyrics(track)


app.jinja_env.globals.update(lyrics=get_song_lyrics)

manager = Manager()
_update_stack = manager.list()


# Load settings
try:
    logger.info("Loading settings from file...")
    settings = load(open('/etc/pmv/settings.json'))
    defaults.set_missing_as_default(settings)
except FileNotFoundError:
    logger.info("No settings file found. Creating a new one with default settings.")
    settings = defaults.default_settings
    defaults.write_settings(settings)

logger.setLevel(settings['log_level'])

logger.debug('Creating database engine')
app.config['SQLALCHEMY_DATABASE_URI'] = settings['database']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init(app)

app.config.update(SECRET_KEY=settings['secret_key'])

if settings['backends']['plex']['enable']:
    logger.info("Using Plex backend.")
    plex = PlexServer(settings['backends']['plex']['server_address'], settings['backends']['plex']['server_token'])
    music = plex.library.section(settings['backends']['plex']['music_library_section'])
    settings['musicLibrary'] = music.locations[0]

    logger.debug("Starting plex alert listener.")
    # thread.start_new_thread(lambda: db.PlexListener(), ())
    Thread(target=db.PlexListener).start()  # TODO End thread

# Login manager configuration
logger.debug("Creating login manager.")
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'users.login'

logger.debug("Setting musicbrainz useragent.")
musicbrainz.set_useragent('Plex Music Viewer', '0.1',
                          'https://github.com/JakeStanger/Plex-Music-Viewer')  # TODO Proper version management


@app.errorhandler(404)
def page_not_found(e, custom_message=None):
    logger.debug("Throwing error 404 (%s)" % custom_message or e)
    return render_template('error.html', code=str(404), message=custom_message or e)


app.jinja_env.globals.update(throw_error=throw_error)


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
        user = db.get_user_by_api_key(api_key)
        if user:
            return user

    return None


@login_manager.user_loader
def get_user(username):
    return db.get_user(username)


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
    parser.add_argument('-l', '--list-routes', action='store_true', help='Dump all the Flask routes and exit')

    args = parser.parse_args()

    if args.update:
        with app.app_context():
            db.init(app)
            if settings['backends']['plex']['enable']:
                db.populate_db_from_plex()
            if settings['backends']['mpd']['enable']:
                db.populate_db_from_mpd()
            sys.exit()
    elif args.list_routes:
        with app.app_context():
            for rule in app.url_map.iter_rules():
                print('%s\t%s\t%s' % (rule.endpoint, rule.rule, rule.methods))
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

# OLD PLEX EVENT LISTENER
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
