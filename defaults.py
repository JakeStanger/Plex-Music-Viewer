from json import loads, dumps

import helper

default_settings = {
    "librarySection": "Music",
    "serverAddress": "http://localhost:32400",
    "interfaceToken": "",
    "searchResults": {
        "artistResults": 10,
        "albumResults": 10,
        "trackResults": 20
    },
    "serverToken": "",
    "database": {
        "user": "",
        "password": "",
        "database": "",  # TODO Automatically create database and tables if missing
        "hostname": "localhost"
    },
    "secret_key": helper.generate_secret_key(),
    "genius_api": "",
    "colors": {
        "textDark": "#111111",
        "textLight": "#ffffff"
    },
    "newUserPerms": [0, 0, 0]
}

track_table = """
create table tracks
(
  library_key  int auto_increment,
  name         text      not null,
  name_sort    text      null,
  artist_key   int       null,
  artist_name  text      not null,
  album_key    int       null,
  album_name   text      null,
  duration     int       null,
  track_num    tinyint   not null,
  disc_num     tinyint   not null,
  download_url text      not null,
  bitrate      mediumint not null,
  size         bigint    not null,
  format       tinytext  not null,
  constraint tracks_library_key_uindex
  unique (library_key),
  constraint tracks_albums_library_key_fk
  foreign key (album_key) references albums (library_key),
  constraint tracks_artists_library_key_fk
  foreign key (artist_key) references artists (library_key)
)
  engine = InnoDB;

alter table tracks
  add primary key (library_key);
"""


def set_defaults():
    pass


def set_missing_as_default(settings: dict):
    for setting in default_settings:
        if setting not in settings:
            settings[setting] = default_settings[setting]

    write_settings(settings)


def write_settings(settings: dict):
    with open('settings.json', 'w') as f:
        f.write(dumps(settings,indent=2))
