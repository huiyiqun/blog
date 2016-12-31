#!/bin/env bash

ROOT_DIR=$(realpath $(dirname "$0")/..)

(
    cd $ROOT_DIR
    pelican content -s publishconf.py
    ghp-import output
    git push origin gh-pages
)
