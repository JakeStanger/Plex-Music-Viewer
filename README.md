# Plex-Music-Viewer
Connects to Plex Media Server and allows browsing and downloading of music

## Setup
- Install requirements from file
- Install `libtorrent` with python bindings support (`libtorrent-rasterbar`)

## Settings

|     Setting    	|                                                                      Description                                                                     	|          Example Value         	|
|:--------------:	|:----------------------------------------------------------------------------------------------------------------------------------------------------:	|:------------------------------:	|
|  serverAddress 	| The URL to the Plex server. This can be the URL your server is running on, or on http://plex.tv, or in theory the URL of anybody else's Plex server. 	| http://localhost:32400         	|
|   serverToken  	| The private token for your Plex server, required to connect to it. Look up how to obtain this if you don't know how.                                 	| s0meString0FR4anDomThings      	|
| interfaceToken 	| A password required to query the API and load the web interface in order to keep your music private.                                                 	| myInterfaceIsReallySecure      	|
| librarySection 	| The name of the Plex library where your music is stored.                                                                                             	| Music                          	|
|  searchResults 	| The number of results to fetch for each category when completing a search query.                                                                     	| artist: 10 album: 10 track: 20 	|
