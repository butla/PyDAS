#!/bin/bash
# this needs to be run with application's virtualenv activated

export VCAP_APP_PORT=5000
export VCAP_SERVICES='{
   "redis28": [
    {
     "credentials": {
      "hostname": "localhost",
      "password": null,
      "port": "5123"
     },
     "name": "requests-store"
    }
   ],
   "user-provided": [
    {
     "credentials": {
      "url": "http://localhost"
     },
     "name": "downloader"
    },
    {
     "credentials": {
      "url": "http://localhost"
     },
     "name": "metadataparser"
    },
    {
     "credentials": {
      "host": "http://localhost"
     },
     "name": "user-management"
    },
    {
     "credentials": {
      "tokenKey": "http://uaa.example.com/token_key"
     },
     "name": "sso"
    }
   ]
  }'
export VCAP_APPLICATION='{"uris": ["localhost:5000"]}'
export REDIS_PORT=5123

CONTAINER=`docker create -p $REDIS_PORT:6379 redis:2.8.22`
docker start $CONTAINER
# TODO wait for the docker to fully start
sleep 1

# Parallelized option
# gunicorn 'data_acquisition.app:get_app()' --bind :$VCAP_APP_PORT --enable-stdio-inheritance --workers `nproc`
gunicorn 'data_acquisition.app:get_app()' --bind :$VCAP_APP_PORT --enable-stdio-inheritance

docker rm -f $CONTAINER
