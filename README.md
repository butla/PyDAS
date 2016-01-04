PyDAS
=====
Python Data Acquisition Service

**Under heavy development**

## TODO (necessary):
1. Special handling of hdfs URIs
1. Validate REDIS connection before starting workers.
1. Split native and non-native requirements.

## TODO (optional):
1. test for logging.
1. Add a script to run locally with Docker end environment.
1. Add configuration parsing solution.
1. All addresses should be HTTPS.
1. Transaction IDs in the further calls and errors.
1. Make it run on Travis.
1. Add Swagger to service.
1. Service test should only call the service through a Bravado generated client. Maybe separate contract tests.
1. Command starting in tests should be taken from manifest.
1. Make talons.auth middleware implement Falcon middleware, because this is confusing
