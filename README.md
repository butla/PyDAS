PyDAS
=====
Python Data Acquisition Service

**Under heavy development**

## TODO (necessary):
1. Hide token in logs
1. test for logging.
1. Uploader support.
1. Add rest of DAS endpoints.
1. Wrap request sending in functions that can log errors.
1. Special handling of hdfs URIs?
1. Handle conversion of Redis data from old DAS.
1. Split native and non-native requirements.
1. Add manifest.yml.
1. Add bumpversion and versioning.

## TODO (optional):
1. Add a script to run locally with Docker end environment.
1. Add configuration parsing solution.
1. All addresses should be HTTPS.
1. Transaction IDs in the further calls and errors.
1. Make it run on Travis.
1. Add Swagger to service.
1. Service test should only call the service through a Bravado generated client. Maybe separate contract tests.
1. Command starting in tests should be taken from manifest.
1. Make talons.auth middleware implement Falcon middleware, because this is confusing

## Old DAS Redis entries
>>> x = cl.hgetall('requests')
>>> x[b'0fad9255-a3ca-4224-8bf2-3bd6ef43748b:0f7294b8-8b71-42cb-8889-a2ba68cbe738']
b'{"id":"0f7294b8-8b71-42cb-8889-a2ba68cbe738","userId":0,"source":"http://fake-csv-server.g
otapaas.eu/fake-csv/2","state":"FINISHED","idInObjectStore":"6f713e2b-5b50-4a3d-833e-d9e691f
5fff6/000000_1","category":"other","title":"test_transfer20150925_111402_418275","timestamps
":{"NEW":1443172449,"DOWNLOADED":1443172449,"FINISHED":1443172450},"orgUUID":"0fad9255-a3ca-
4224-8bf2-3bd6ef43748b","token":"eyJhbGciOiJSUzI1NiJ9.eyJqdGkiOiI5YjNlYWVkMS0yMmNjLTQ4ZWMtYj
EyMC02NWVlNDY5ZWYxMjgiLCJzdWIiOiJjOWY3NTgyYi00ZDhkLTRmY2YtOTRiOC00YWUxYzAyZmMzZDciLCJzY29wZS
I6WyJzY2ltLnJlYWQiLCJjb25zb2xlLmFkbWluIiwiY2xvdWRfY29udHJvbGxlci5hZG1pbiIsInBhc3N3b3JkLndyaX
RlIiwic2NpbS53cml0ZSIsIm9wZW5pZCIsImNsb3VkX2NvbnRyb2xsZXIud3JpdGUiLCJjbG91ZF9jb250cm9sbGVyLn
JlYWQiXSwiY2xpZW50X2lkIjoiZGV2ZWxvcGVyX2NvbnNvbGUiLCJjaWQiOiJkZXZlbG9wZXJfY29uc29sZSIsImF6cC
I6ImRldmVsb3Blcl9jb25zb2xlIiwiZ3JhbnRfdHlwZSI6ImF1dGhvcml6YXRpb25fY29kZSIsInVzZXJfaWQiOiJjOW
Y3NTgyYi00ZDhkLTRmY2YtOTRiOC00YWUxYzAyZmMzZDciLCJ1c2VyX25hbWUiOiJ0cnVzdGVkLmFuYWx5dGljcy50ZX
N0ZXJAZ21haWwuY29tIiwiZW1haWwiOiJ0cnVzdGVkLmFuYWx5dGljcy50ZXN0ZXJAZ21haWwuY29tIiwicmV2X3NpZy
I6ImRmMGQxZjQ2IiwiaWF0IjoxNDQzMTcxODIxLCJleHAiOjE0NDQzODE0MjEsImlzcyI6Imh0dHBzOi8vdWFhLmRlbW
90cnVzdGVkYW5hbHl0aWNzLmNvbS9vYXV0aC90b2tlbiIsInppZCI6InVhYSIsImF1ZCI6WyJkZXZlbG9wZXJfY29uc2
9sZSIsInNjaW0iLCJjb25zb2xlIiwiY2xvdWRfY29udHJvbGxlciIsInBhc3N3b3JkIiwib3BlbmlkIl19.aLmBNhG48
UtbjchxLKuzuub4zHbe17m7LgH8oj6V9ufMpDAN7433_ehngwpMwnrWvRZxmSyounJwyPw2behW4bKwNzor34f2XzzEt
I8Z9d6NK9zA886KMuzCjfPjEdwXzA3Isk0Ic-lcURrXcPJ7ec_he61TO3QGp42O-2hNvpA","publicRequest":fals
e}'