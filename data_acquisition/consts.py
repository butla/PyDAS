"""
Constant values used throughout the app.
"""

CALLBACK_PATH = '/v1/das/callback'
ACQUISITION_PATH = '/rest/das/requests'
GET_REQUEST_PATH = ACQUISITION_PATH + '/{req_id}'
DOWNLOAD_CALLBACK_PATH = CALLBACK_PATH + '/downloader/{req_id}'
DOWNLOADER_PATH = '/rest/downloader/requests'
METADATA_PARSER_PATH = '/rest/metadata'
METADATA_PARSER_CALLBACK_PATH = CALLBACK_PATH + '/metadata/{req_id}'
UPLOADER_REQUEST_PATH = CALLBACK_PATH + '/uploader'
