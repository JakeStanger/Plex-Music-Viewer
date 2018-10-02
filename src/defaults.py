from json import dumps

from src import helper

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
        "database": "",
        "hostname": "localhost"
    },
    "secret_key": helper.generate_secret_key(),
    "genius_api": "",
    "colors": {
        "textDark": "#111111",
        "textLight": "#ffffff"
    },
    "newUserPerms": [0, 0, 0],
    "lastfm_key": "",
    "album_art_fetchers": ['plex', 'musicbrainz', 'lastfm', 'local'],
    "log_level": "INFO"
}

default_tables = {
    'users': """
        create table users
        (
          user_id     bigint auto_increment
            primary key,
          username    text                   not null,
          password    text                   not null,
          music_perms tinyint(6) default '3' not null,
          movie_perms tinyint(6) default '3' not null,
          tv_perms    tinyint(6) default '3' not null,
          is_admin    tinyint(1) default '0' not null,
          is_deleted  tinyint(1) default '0' not null
        );
    """,
    'api_keys': """
        create table api_keys
        (
          key_id  bigint auto_increment,
          user_id bigint not null,
          value   text   not null,
          constraint api_keys_key_id_uindex
          unique (key_id),
          constraint api_keys_users_user_id_fk
          foreign key (user_id) references users (user_id)
            on update cascade
            on delete cascade
        );

        alter table api_keys
            add primary key (key_id);
    """,
    'artists': """
        create table artists
        (
          library_key int    not null,
          name        text   not null,
          name_sort   text   not null,
          thumb       bigint null,
          album_count int    not null,
          constraint artists_library_key_uindex
          unique (library_key)
        );
        
        alter table artists
          add primary key (library_key);
    """,
    'albums': """
        create table albums
        (
          library_key int         not null,
          name        text        not null,
          name_sort   text        not null,
          artist_key  int         not null,
          artist_name text        not null,
          year        smallint(6) not null,
          genres      text        null,
          thumb       bigint      null,
          track_count smallint(6) not null,
          total_size  bigint      not null,
          constraint albums_library_key_uindex
          unique (library_key),
          constraint albums_artists_library_key_fk
          foreign key (artist_key) references artists (library_key)
            on update cascade
            on delete cascade
        );
            
            alter table albums
              add primary key (library_key);
    """,
    'tracks': """
        create table tracks
        (
          library_key  int auto_increment,
          name         text      not null,
          name_sort    text      not null,
          artist_key   int       not null,
          artist_name  text      not null,
          album_key    int       not null,
          album_name   text      not null,
          duration     int       not null,
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
        );
        
        alter table tracks
          add primary key (library_key);
    """
}


def set_missing_as_default(settings: dict):
    for setting in default_settings:
        if setting not in settings:
            settings[setting] = default_settings[setting]

    write_settings(settings)


def write_settings(settings: dict):
    with open('settings.json', 'w') as f:
        f.write(dumps(settings, indent=2))