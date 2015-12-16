from data_acquisition.acquisition_request import AcquisitionRequest
from data_acquisition.cf_app_utils.auth import USER_MANAGEMENT_PATH

RSA_2048_PRIV_KEY = '''-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAosXzctOonWuZTCZR6KX4K7kepQwacvSh5YRrDDR7QSVWm6+l
2FobhobvNJ45UprWk/BwJYpk6V/IUtTvPtHGKsjorTvJvGQ5k/33oMcbwU3yLE1w
iYXwuc6W04CCP/wu+3nF826RhWkwb9xngHUWOHA5njQ6BBOFaMfHXbRbiyKOR9Q0
q+TdaHDX8f+bgQEgwZn/DfGfB9OZ1KEWKsrAz+eGGCY/o+EloiiNzyRdWl8oKj7o
boY2WMoK6E3iZcqU07fM27SqTr1yj+y+9RKVWibOERVGlxPy/w/6ckU23yDM3wjV
mD9UpZZS0jx6pe84vHnyVi/kT7ViVnE3mK3aCQIDAQABAoIBACcx7WZYC0Ek2Lwa
ehzAYlr876EkofXObHGdCj3dIVTVjd5dVF0djYU+Vrlf5EO83zCudALGKXh8xPsV
JSsGTmadDFIylGhV5ft56zf+2fMZNthuKUwkQYwsb+ssBbEso4+QihcNJ+NtKem1
tAKdryUV+Pncb5/tp3FMsfghZu3AmQGOIlz9Y7xOt3e7UY6rIsIHSBMW11PZ83r0
NxQl1hOnChZxnMhDDaaVrRHc+PdSqMFpCjDVwRW2Dl4XbbqTiS979L++XSt25eUn
uobT6h3ErNduiIC+eb89MuZ3xvlER6XA81aPeaLxpqE6ua8g+DxIyVemTBLCqz3u
dBHEKWUCgYEA1eHt5gGXZ4EPyNwMSvC4LOe4laRQ/NNdTWqhZXgtzYaJEY0VwWuM
+h/QKsT3fhPP/IOj1vEtusjfD5sNb6hlwR0rRNFiD+p1U31Y4FYUnr/4VPt/ivGl
EPn/GBJkpsTTOF2W7tjAQGNswQybTC1JQ1nVUL4IChIVlwESlrjYQEcCgYEAwtOK
yKtP9pT65WuXDiaadhyFH3dvDWOQ/p1c2lVziCX4eLRWkY8JyxdbCWNUt11XURcT
knT1sRZdJq1Wk/Zk0IypTjawKDD8jaQguxHN8mwQzyge4AtCXJT4+IG84itZKf2+
pXZWiX0C4wOPQfCqHycoEXh/AHV7GZhW01qRCy8CgYATF3m+4EF9kb2w9kN6pQYr
q/uEEAjSqKNZd700a4fbIrk1gdyBSXJqGVDhoHdfH7GfHrkPRLQKSkfvAq4uW1/J
3yqvl+ki9pDGhRfb3pM0oHowS8rUwkEzxL0KjwnBASzBiUkhxONUXAunJ9Ls99Xk
Vy59aJkbHQYkVoosPg+/nQKBgQCKopOQZe85zRuYI25TAH9LatID6S4Z/e7Qb9QB
/Wp/yF0+Lz2myH00ioMadBd1f7NBncUso5OtlvdkLVZ9ZYipql5TrLC/eNROSiuM
UogVaHaxoqAN15U6YjukQlXRLv181vZRsZq0rUNfnUnUp1e3YVquy+q7vd2CAhhO
v5SUuwKBgCThdYIXyuuKmWLK4hhrR1p84kynBp17UHHmgXmYgy1eoNbsX9rZMEgU
zGdjlenIFdHIMe4FfIFJXJLDipTFysw79Ul/nHDxDqbhG5NUnZIVSUa9d9JTbAHN
JoyYU4gs1vNOe499ZmT4pmoXQLdBbLIgTm1bb808dgpm5ZTGibnz
-----END RSA PRIVATE KEY-----
'''

RSA_2048_PUB_KEY = '''-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAosXzctOonWuZTCZR6KX4
K7kepQwacvSh5YRrDDR7QSVWm6+l2FobhobvNJ45UprWk/BwJYpk6V/IUtTvPtHG
KsjorTvJvGQ5k/33oMcbwU3yLE1wiYXwuc6W04CCP/wu+3nF826RhWkwb9xngHUW
OHA5njQ6BBOFaMfHXbRbiyKOR9Q0q+TdaHDX8f+bgQEgwZn/DfGfB9OZ1KEWKsrA
z+eGGCY/o+EloiiNzyRdWl8oKj7oboY2WMoK6E3iZcqU07fM27SqTr1yj+y+9RKV
WibOERVGlxPy/w/6ckU23yDM3wjVmD9UpZZS0jx6pe84vHnyVi/kT7ViVnE3mK3a
CQIDAQAB
-----END PUBLIC KEY-----
'''

# token created with:
# jwt.encode(payload={'scope': ['nothing'], 'a': 'b'}, key=RSA_2048_PRIV_KEY, algorithm='RS256').decode()
TEST_AUTH_HEADER = 'bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJzY29wZSI6WyJub3RoaW5nIl0sImEiOiJiIn0.egZuJIZpA-WGr_IXXuV8Q2aY5mFdFGC3nZvsN33hJxzFtDie07XYjsNiSmCAgxInZEatE4f7GTt9qa1tuKibAdgr4jxcoHbCN2CqDAkEwuloNciInJbRMBk_lK3eCacFc46htVu1qrifvvJRBaxsunBj6g8mbdNiVV1PKyRgTuG0WRBI8OLBuHK5r2jXPNhkStsz2blZlXs3T2SgjPRF4jR0hAJAO8wpZGqxxFA4fzjBHG-CVmuxeAMv5APESpM_K6J_rVMBX8jFPiwB34EJZ1bQXyVn2ZcpmoOYTXInQu5nj5vwIHD2idvoZ_VniMjJuPrDJCZ-aVKbVJKbXE3rBg'

# jwt.encode(payload={'scope': ['console.admin'], 'a': 'b'}, key=RSA_2048_PRIV_KEY, algorithm='RS256').decode()
TEST_ADMIN_AUTH_HEADER = 'bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJzY29wZSI6WyJjb25zb2xlLmFkbWluIl0sImEiOiJiIn0.I4pekwOqNH6lGo656LZiM75ogUIalI_pUj-GbWvtgcp_dlyv47FGpU9zdO3iwaCEU0QXdf-Eoy9aC7wE6sstp-5k739vfCgZ_xp1J9yJp0Mnm7QiNNN4I4Zs5C34g341shJozmrS9LbPPZtVsI2cRG31oJ-TlIavYj7ZAqfLgdAMlIm73coIkIAusKdgtPZT-FxDeWMs5-BlMgTcpM2mGOWba1PDHagB0c_GbH40vhapcnJdpDNdufSLcp_oVAveu8__cVSHehDRx_GDtK8A656auc4R8XRZq_oL24h8hqEIV155plOW3CAh4dlpXnVl4E1HxO2cEixHCSyBH358_g'

TEST_ORG_UUID = 'fake-org-uuid'

FAKE_PERMISSION_SERVICE_URL = 'http://fake-user-management'
FAKE_PERMISSION_URL = FAKE_PERMISSION_SERVICE_URL + USER_MANAGEMENT_PATH

TEST_DOWNLOAD_REQUEST = {
    'orgUUID': TEST_ORG_UUID,
    'publicRequest': True,
    'source': 'http://some-fake-url',
    'category': 'other',
    'title': 'My test download',
}

TEST_ACQUISITION_REQ_JSON = dict(TEST_DOWNLOAD_REQUEST)
TEST_ACQUISITION_REQ_JSON.update({
    'state': 'VALIDATED',
    'id': 'fake-id',
    'timestamps': {},
})

TEST_ACQUISITION_REQ = AcquisitionRequest(**TEST_ACQUISITION_REQ_JSON)

TEST_ACQUISITION_REQ_STR = str(TEST_ACQUISITION_REQ)

TEST_DOWNLOAD_CALLBACK = {
    'id': TEST_ACQUISITION_REQ_JSON['id'],
    'state': 'DONE',
    'savedObjectId': 'fake-saved-id',
    'objectStoreId': 'hdfs://some-fake-hdfs-path',
}

TEST_VCAP_SERVICES_TEMPLATE = """
 {{
  "redis28": [
   {{
    "credentials": {{
     "hostname": "{redis_host}",
     "password": {redis_password},
     "port": "{redis_port}"
    }},
    "name": "requests-store"
   }}
  ],
  "user-provided": [
   {{
    "credentials": {{
     "url": "http://{downloader_host}"
    }},
    "name": "downloader"
   }},
   {{
    "credentials": {{
     "url": "http://{metadata_parser_host}"
    }},
    "name": "metadataparser"
   }},
   {{
    "credentials": {{
     "host": "http://{user_management_host}"
    }},
    "name": "user-management"
   }},
   {{
    "credentials": {{
     "tokenKey": "{verification_key_url}"
    }},
    "name": "sso"
   }}
  ]
 }}"""

TEST_VCAP_APPLICATION = """
{
  "uris": [
   "das.example.com"
  ]
}"""
