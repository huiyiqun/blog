#!bash

ROOT_DIR=$(realpath $(dirname "$0")/..)

(
    cd $ROOT_DIR
    pelican content -s publishconf.py
    php-import output
    git push origin gh-pages
)
