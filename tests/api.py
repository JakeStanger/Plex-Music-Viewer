from requests import get
from json import dumps, loads
from timeit import default_timer as timer


def load_and_dump(res):
    return dumps(loads(res), indent=2)


def make_request(url):
    start = timer()
    base_url = 'http://localhost:5000'
    headers = {"Authorization": "Basic 5gwae1JAjGOOnWts3sdXBOfLyO6CwrCmVvL8bXE10DqeL1w9fs8LOX8EzHy7a16S",
               "Accept": "application/json"}
    print(url)
    print(loads(get(base_url + url, headers=headers).content))
    print("Request time: ", round((timer() - start)*1000))
    print("----------------")


print("----Test API JSON requests----")
make_request('/music/artist')
make_request('/music/artist/72')
make_request('/music/album/544')
make_request('/music/track/6660')