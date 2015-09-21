#!/bin/bash
export VCAP_APP_PORT=5000
export REDIS_PORT=5123

CONTAINER=`docker create -p $REDIS_PORT:6379 redis:2.8.22`
docker start $CONTAINER

gunicorn 'app:get_app()' --bind :$VCAP_APP_PORT --enable-stdio-inheritance --workers `nproc`

docker stop $CONTAINER
docker rm $CONTAINER