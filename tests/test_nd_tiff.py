from pathlib import Path

import numpy as np
import pytest

from slicedimage._formats import tiff_reader, tiff_writer


def test_2d_tiff(tmp_path):
    path = Path(str(tmp_path / "2d.tiff"))
    data = np.random.random((5, 6))
    tiff_writer()(path, data)
    read = tiff_reader()(path)
    assert np.all(data == read)


def test_3d_tiff(tmp_path):
    path = Path(str(tmp_path / "3d.tiff"))
    data = np.random.random((5, 6, 7))
    tiff_writer()(path, data)
    read = tiff_reader()(path)
    assert np.all(data == read)


def test_4d_tiff(tmp_path):
    path = Path(str(tmp_path / "4d.tiff"))
    data = np.random.random((5, 6, 7, 8))
    with pytest.raises(ValueError):
        tiff_writer()(path, data)
