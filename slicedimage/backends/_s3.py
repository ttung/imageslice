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
        parsed = urllib.parse.urlparse(baseurl)
        assert parsed[0].lower() == "s3"

        self._bucket = parsed[1]
        if parsed[2][0] == "/":
            self._basepath = PurePosixPath(parsed[2][1:])
        else:
            self._basepath = PurePosixPath(parsed[2])
        self._s3_config = s3_config

    def read_contextmanager(self, name, checksum_sha256=None):
        key = str(self._basepath / name)
        return _S3ContextManager(self._bucket, key, checksum_sha256, self._s3_config)


class _S3ContextManager:
    def __init__(self, s3_bucket, s3_key, checksum_sha256, s3_config):
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key
        self.checksum_sha256 = checksum_sha256
        self.s3_config = s3_config

    def __enter__(self):
        unsigned_requests = self.s3_config.get(S3Backend.CONFIG_UNSIGNED_REQUESTS_KEY, False)

        if unsigned_requests:
            resource_config = Config(signature_version=UNSIGNED)
        else:
            resource_config = None

        session = boto3.session.Session()
        s3 = session.resource("s3", config=resource_config)
        bucket = s3.Bucket(self.s3_bucket)
        s3_obj = bucket.Object(self.s3_key)
        self.buffer = BytesIO()
        s3_obj.download_fileobj(self.buffer)
        self.buffer.seek(0)
        verify_checksum(self.buffer, self.checksum_sha256)
        return self.buffer.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.buffer.__exit__(exc_type, exc_val, exc_tb)
