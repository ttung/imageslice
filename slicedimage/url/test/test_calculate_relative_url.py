from ..path import calculate_relative_url


def _test(baseurl: str, name_or_url: str, expected_output: str):
    result = calculate_relative_url(baseurl, name_or_url)
    assert result == expected_output


def test_samelevel():
    _test("http://example.com/abc", "http://example.com/def", "def")
    _test("http://example.com/dir/abc", "http://example.com/dir/def", "def")
    _test("http://example.com/abc;ab", "http://example.com/def;de", "def;de")
    _test("http://example.com/abc?ab", "http://example.com/def?de", "def?de")
    _test("http://example.com/abc#ab", "http://example.com/def#de", "def#de")


def test_nested():
    _test("http://example.com/abc", "http://example.com/dir/def", "dir/def")
    _test("http://example.com/dir/abc", "http://example.com/def", "http://example.com/def")


def test_different_scheme():
    _test("http://example.com/abc", "https://example.com/dir/def", "https://example.com/dir/def")
