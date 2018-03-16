import os
import libtorrent as lt
import time

MUSIC = "/libraries/Music"
TORRENTS = "/var/www/music/public_html/torrents"

ses = lt.session()
ses.listen_on(6881, 6891)

albums = [x[0] for x in os.walk(MUSIC)]
for album in albums:

    # Skip non-album directories
    if album.count("/") - MUSIC.count("/") != 2:
        continue

    albumName = album.split("/")[-1]
    albumPath = album.rsplit("/", 1)[0].replace(MUSIC, TORRENTS)

    print("--Seeding torrent for:", albumName + "--")
    print(albumPath + '/' + albumName + ".torrent")

    # Seed torrent
    try:
        h = ses.add_torrent(
            {'ti': lt.torrent_info(albumPath + '/' + albumName + ".torrent"), 'save_path': albumPath.replace(TORRENTS, MUSIC), 'seed_mode': True})
        print("Total size_formatted: " + str(h.status().total_wanted) + "\n")
    except:
        print("Error for: " + albumName)

while True:
    time.sleep(0.1)
