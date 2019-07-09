import urllib.parse
from io import BytesIO
from pathlib import PurePosixPath

import boto3
from botocore import UNSIGNED
from botocore.config import Config

from ._base import Backend, verify_checksum

RETRY_STATUS_CODES = frozenset({500, 502, 503, 504})


class S3Backend(Backend):
    CONFIG_UNSIGNED_REQUESTS_KEY = "unsigned-requests"

    def __init__(self, baseurl, s3_config):
        unsigned_requests = s3_config.get(S3Backend.CONFIG_UNSIGNED_REQUESTS_KEY, False)

        if unsigned_requests:
            resource_config = Config(signature_version=UNSIGNED)
        else:
            resource_config = None

        parsed = urllib.parse.urlparse(baseurl)
        assert parsed[0].lower() == "s3"
        session = boto3.session.Session()
        s3 = session.resource("s3", config=resource_config)
        self._bucket = s3.Bucket(parsed[1])

        if parsed[2][0] == "/":
            self._basepath = PurePosixPath(parsed[2][1:])
        else:
            self._basepath = PurePosixPath(parsed[2])

    def read_contextmanager(self, name, checksum_sha256=None):
        key = str(self._basepath / name)
        print(key)
        return _S3ContextManager(self._bucket.Object(key), checksum_sha256)


class _S3ContextManager:
    def __init__(self, s3_obj, checksum_sha256):
        self.s3_obj = s3_obj
        self.checksum_sha256 = checksum_sha256

    def __enter__(self):
        self.buffer = BytesIO()
        self.s3_obj.download_fileobj(self.buffer)
        self.buffer.seek(0)
        verify_checksum(self.buffer, self.checksum_sha256)
        return self.buffer.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.buffer.__exit__(exc_type, exc_val, exc_tb)
