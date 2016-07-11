PyDAS
=====

[![SnapCI Build](https://snap-ci.com/butla/PyDAS/branch/master/build_image)](https://snap-ci.com/butla/PyDAS/branch/master)
[![Coverage Status](https://coveralls.io/repos/github/butla/PyDAS/badge.svg?branch=master)](https://coveralls.io/github/butla/PyDAS?branch=master)
[![Requirements Status](https://requires.io/github/butla/PyDAS/requirements.svg?branch=master)](https://requires.io/github/butla/PyDAS/requirements/?branch=master)

Python rewrite of [TAP's DAS](https://github.com/trustedanalytics/data-acquisition).
Functionally the same as DAS from 2016-03-20 (version 0.5.8).

It has full test coverage and some useful integration tests.
It doesn't use Kafka, because it doesn't need to.

## Deployment
* `./build_for_cf.sh`
* `cf push`

## Testing
* Install [Docker](https://docs.docker.com/linux/step_one/)
* Preparing a virtual environment, running the tests and quality check: `tox`
* Running just the tests without quality checks (from virtualenv): `py.test tests/`

## Other development activities
* Activating virtualenv created by Tox: `source .tox/py34/bin/activate`
* Bumping the version: (while in virtualenv) `bumpversion --alow-dirty patch`
* Running the application: (you need to configure addresses in the script first) `./run_app.sh`

## Dependency management
Due to shenanigans with offline deployments the requirements need to go into two files:
* Add dependencies that need to compiled on the target platform and their dependencies `requirements-native.txt`.
* Pure Python dependencies should go to `requirements-normal.txt`.
* Running `./build_for_cf.sh` will generate `requirements.txt` that can be used to deploy the app.

## TODO (optional):
1. Extract a general configuration parsing solution.
1. Add Swagger to service.
1. Service test should only call the service through a Bravado generated client. Maybe separate contract tests.
1. Merge `simulate_falcon_request` from tests into Falcon.
1. Add a script to run locally with Docker, environment and Mountebank mocks.
1. All addresses should be HTTPS.
1. Transaction IDs in the further calls and errors.
1. Command starting in tests should be taken from manifest.
1. Make talons.auth middleware implement Falcon middleware, because this is confusing
