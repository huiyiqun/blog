#!/bin/env bash

ROOT_DIR=$(realpath $(dirname "$0")/..)

trap 'killall' INT
trap 'true' TERM

killall() {
    echo "*** Shuting down... ***"
    kill -TERM 0
    wait
    echo DONE
}

(
    cd $ROOT_DIR
    pelican content -r &
    sleep 1 # wait for output is created
    cd output
    python -m pelican.server &
    sleep 2 # wait for pelican server is up
    echo 'Page is availabe at "http://localhost:8000/, stopped by Ctrl-C."'
)

cat > /dev/null
