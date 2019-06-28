import json
import pytest

from slicedimage.backends import ChecksumValidationError, S3Backend


@pytest.mark.parametrize(
    "expected_checksum",
    ["e50af7fc87769124bb4e8edd9853518578e5d7a143aec77bfe97857a0e3f00e0", None]
)
def test_checksum_good_or_not_present(expected_checksum):
    s3backend = S3Backend(
        "s3://starfish.data.spacetx/osmFISH/formatted/20190626",
        {
            S3Backend.CONFIG_UNSIGNED_REQUESTS_KEY: True,
        }
    )

    with s3backend.read_contextmanager("experiment.json", expected_checksum) as cm:
        data = cm.read()
        data_s = data.decode("UTF-8")
        parsed = json.loads(data_s)
        assert parsed['version'] == "5.0.0"


def test_checksum_bad():
    s3backend = S3Backend(
        "s3://starfish.data.spacetx/osmFISH/formatted/20190626",
        {
            S3Backend.CONFIG_UNSIGNED_REQUESTS_KEY: True,
        }
    )

    with pytest.raises(ChecksumValidationError):
        with s3backend.read_contextmanager(
                "experiment.json",
                "e50af7fc87769124bb4e8edd9853518578e5d7a143aec77bfe97857a0e3f00e1") as cm:
            data = cm.read()
            parsed = json.loads(data)
            assert parsed['version'] == "5.0.0"
