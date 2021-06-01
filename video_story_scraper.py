#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Define a web scraping spider class to scrape a 
single Russian news story and download:
1. The story metadata
2. The video transcript
3. The video
"""

# Python standard library
import json
import pathlib
import time
from urllib.parse import urlparse
from urllib.request import urlretrieve

# External packages
import moviepy.editor
import requests
from bs4 import BeautifulSoup


def _get_json_from_response(response):
    return response.json() if response and response.status_code == 200 else None

