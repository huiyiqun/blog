#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

# This file is only used if you use `make publish` or
# explicitly specify it as your config file.

import os
import sys
sys.path.append(os.curdir)
from pelicanconf import *

SITEURL = 'https://blog.huiyiqun.me'
# RELATIVE_URLS = False

FEED_ALL_ATOM = 'feed.xml'
SOCIAL = SOCIAL + (('rss', '/'.join((SITEURL, FEED_ALL_ATOM))), )

DELETE_OUTPUT_DIRECTORY = True

# Following items are often useful when publishing

DISQUS_SITENAME = "huiyiqun"
GOOGLE_ANALYTICS = "UA-89649249-1"
GOOGLE_TAG_MANAGER = "GTM-NW57T8B"
