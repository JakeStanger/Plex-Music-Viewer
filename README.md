# Plex-Music-Viewer
A web application written in Python with Bootstrap 4 to integrate with your Plex
music library.

## Dependencies
- Python dependencies can be installed using 
`pip -r requirements.txt`.
Each one and its use is included below.
- Depending on your database engine you may need to install further dependencies:
    - MySQL: `# apt install libmysqlclient-dev` etc...
- For optional bittorrent support `libtorrent` with python 
bindings support (`libtorrent-rasterbar`) is required.
You will have to find the correct package for your OS.

### Python Dependency Usages
###### TODO Finish descriptions; put these in a better order.
- `musicbrainzngs` is used for fetching album art from
MusicBrainz.
- `requests` is used for sending extra requests to
 APIs where existing libraries miss some required data.
- `python-magic`
- `werkzeug` is a flask dependency, also used for routing.
- `scipy`
- `numpy`
- `plexapi` is used in order to connect to the Plex server
if the Plex backend is being used.
- `flask` is the web microframework.
- `xmltodict` is used when getting some extra data from
the Plex server, as the server will only return a bizarrely
formatted XML document and refuses to give JSON.
- `simplejson` is used for converting JSON to and from
dictionaries.
- `pillow`
- `Image`
- `flask-mysql` is used to query the local database.
- `flask-login` is used to help manage user accounts.
- `lyricsgenius` is used for fetching track lyrics from
Genius.
- `pylast` is used for fetching album art from Last.fm

## Settings
###### TODO Create table describing settings

## Fetching Lyrics
Fetching lyrics requires a Genius API client access token.
One must sign up for a Genius account and create an API
client to obtain the access token. This can be done at the
link below:

https://genius.com/api-clients

Once this key is put in the settings, restart the application
if it is running and lyrics will automatically be fetched.

### Local Lyrics
Fetched lyrics are cached in the `lyrics` folder in the
format `Artist - Track.txt`. The application will check
here before trying to download lyrics. 

This also means if you do not wish to use Genius, you
may place lyrics in this folder and the application will
display them as normal.

## Fetching album art
In the settings file is a list of album art fetchers
in the order they will be tried.

By default, Plex is first in the list. If using Plex as 
the backend, all album art will automatically be fetched 
from the server.

### last.fm
Fetching album art from last.fm requires an API key. This
will require a last.fm account. You can obtain a key at
the link below.

https://www.last.fm/api/account/create