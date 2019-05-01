from packaging import version

from slicedimage import VERSIONS


def test_version_increasing_order():
    """Verifies that the VERSIONS list is in increasing order."""
    for ix in range(1, len(VERSIONS)):
        prev_version = VERSIONS[ix - 1]
        curr_version = VERSIONS[ix]

        assert version.parse(prev_version.VERSION) < version.parse(curr_version.VERSION)
