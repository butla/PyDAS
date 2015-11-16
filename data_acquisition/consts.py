"""
Constant values used throughout the app.
"""

CALLBACK_PATH = '/v1/das/callback'
ACQUISITION_PATH = '/rest/das/requests'
DOWNLOAD_CALLBACK_PATH = CALLBACK_PATH + '/downloader/{req_id}'
DOWNLOADER_PATH = '/rest/downloader/requests'
METADATA_PARSER_PATH = '/rest/metadata'
# TODO only an enum is sent there
METADATA_PARSER_CALLBACK_PATH = CALLBACK_PATH + '/metadata/{req_id}'
USER_MANAGEMENT_PATH = '/rest/orgs/permissions'
