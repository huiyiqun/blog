#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals
from os import path

root_path = path.dirname(__file__)
plugin_path = path.join(root_path, 'plugins')

AUTHOR = 'Hui Yiqun'
SITENAME = 'Notepad'
SITEURL = ''

PATH = 'content'

TIMEZONE = 'Asia/Shanghai'

DEFAULT_LANG = 'zh'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Blogroll
LINKS = (('TUNA', 'https://tuna.moe/'),)

# Social widget
SOCIAL = (('Github', 'https://github.com/huiyiqun'),
          ('Telegram', 'https://telegram.me/huiyiqun'),)

DEFAULT_PAGINATION = False

# Same path as jekyll
ARTICLE_URL = '{date:%Y}/{date:%m}/{date:%d}/{slug}.html'
ARTICLE_SAVE_AS = ARTICLE_URL

# Plugins
PLUGIN_PATHS = [plugin_path, ]
PLUGINS = [
    'render_math',
]

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True
