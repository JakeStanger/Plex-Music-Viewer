#!/usr/bin/env python3

import requests
print(requests.post('http://music.jakestanger.com/update_database').status_code)
