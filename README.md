PyDAS
=====
Python Data Acquisition Service

**Under heavy development**

## TODOs:
1. Add callback handling.
1. Add rest of DAS endpoints.
1. Add logic for checking authorization with user-management (generate client with Bravado, have middleware that reads json and replaces stream with a new bytes.IO).
1. Split native and non-native requirements.
1. Add manifest.yml.
1. Add bumpversion and versioning.
1. Add a script to run locally with Docker end environment.
1. Add configuration parsing solution.
1. All addresses should be HTTPS.
1. Add custom error handling that sends the timestamp.
1. Make it run on Travis.
1. Add Swagger to service.
1. Service test should only call the service through a Bravado generated client.
1. Command starting in tests should be taken from manifest.
1. Make talons.auth middleware implement Falcon middleware, because this is confusing
