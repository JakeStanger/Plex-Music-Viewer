import os
import re
from io import BytesIO
from urllib.request import urlopen

import numpy as np
import scipy
import scipy.cluster
import scipy.misc
from PIL import Image

import app


def get_friendly_thumb_id(thumb_id):
    return '-'.join(num for num in re.findall('\\d+', thumb_id))


def save_image_to_disk(thumb_id, image, width: int=None):
    if not os.path.exists('images'):
        os.makedirs('images')

    image.save("images/%s_%s.png" % (get_friendly_thumb_id(thumb_id), str(width) if width else ''), 'PNG', quality=90)


def read_image_from_disk(thumb_id, width: int=None):
    try:
        return Image.open("images/%s_%s.png" % (get_friendly_thumb_id(thumb_id), str(width) if width else ''))
    except FileNotFoundError:
        return None


def get_raw_image(thumb_id: str, width: int=None):
    if thumb_id.startswith('/'):
        thumb_id = thumb_id[1:]

    cached = read_image_from_disk(thumb_id, width)
    if cached:
        return cached

    settings = app.get_settings()

    thumb_id = '/' + thumb_id
    url = settings['serverAddress'] + thumb_id + "?X-Plex-Token=" + settings['serverToken']

    try:
        file = BytesIO(urlopen(url).read())
        image = Image.open(file)

        if width:
            size = int(width), int(width)
            image.thumbnail(size, Image.ANTIALIAS)

        save_image_to_disk(thumb_id, image, width)
        return image
    except Exception as e:
        print(e)
        app.throw_error(400, "invalid thumb-id")


def get_image(thumb_id, width=None):
    image = get_raw_image(thumb_id, width)
    tmp_image = BytesIO()
    image.save(tmp_image, 'PNG', quality=90)
    tmp_image.seek(0)

    return tmp_image


def get_predominant_colour(thumb_id):
    NUM_CLUSTERS = 5

    image = get_raw_image(thumb_id, width=150)
    ar = np.asarray(image)
    shape = ar.shape
    ar = ar.reshape(scipy.product(shape[:2]), shape[2]).astype(float)

    codes, dist = scipy.cluster.vq.kmeans(ar, NUM_CLUSTERS)

    vecs, dist = scipy.cluster.vq.vq(ar, codes)  # assign codes
    counts, bins = scipy.histogram(vecs, len(codes))  # count occurrences
    index_max = scipy.argmax(counts)  # find most frequent
    peak = codes[index_max]

    colour = '#'
    for c in peak:
        char = str(hex(int(c)))[2:]
        if len(char) == 1:
            char = '0' + char

        colour += char

    return colour


def get_complimentary_colour(hex_code: str):
    if hex_code.startswith('#'):
        hex_code = hex_code[1:]

    rgb = (hex_code[0:2], hex_code[2:4], hex_code[4:6])
    comp = ['%02X' % (255 - int(a, 16)) for a in rgb]
    return '#' + ''.join(comp)


def get_text_colour(hex_code: str):
    if hex_code.startswith('#'):
        hex_code = hex_code[1:]

    rgb = (int(hex_code[0:2], 16), int(hex_code[2:4], 16), int(hex_code[4:6], 16))

    # W3C formula for brightness
    brightness = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000

    # Brightness is from 0-255
    if brightness > 170:
        return '#111111'
    else:
        return '#ffffff'
