#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals
from os import path

root_path = path.dirname(__file__)
plugin_path = path.join(root_path, 'plugins')
theme_path = path.join(root_path, 'themes')

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
SOCIAL = (('github', 'https://github.com/huiyiqun'),
          ('stack-overflow', 'https://stackoverflow.com/users/2825773/given92'),
          ('google-plus', 'https://plus.google.com/u/0/107187513671494024284'),
          ('telegram', 'https://telegram.me/huiyiqun'),)

DEFAULT_PAGINATION = False

# Same path as jekyll
ARTICLE_URL = '{date:%Y}/{date:%m}/{date:%d}/{slug}.html'
ARTICLE_SAVE_AS = ARTICLE_URL

# Plugins
PLUGIN_PATHS = [plugin_path, ]
PLUGINS = [
    'render_math',
]

THEME = path.join(theme_path, 'Flex')

# Uncomment following line if you want document-relative URLs when developing
RELATIVE_URLS = True

# Additional configuration for the current theme
SITETITLE = SITENAME
SITESUBTITLE = 'The Power of Writing'
SITELOGO = 'https://secure.gravatar.com/avatar/e96680ba97e70a013f818edde6753ca8?s=120'
BROWSER_COLOR = 'white'
OG_LOCALE = 'zh_CN'
COPYRIGHT_YEAR = '2016'
PYGMENTS_STYLE = 'native'
