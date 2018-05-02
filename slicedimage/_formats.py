import enum


def skimage_reader():
    # lazy load skimage
    import skimage.io

    return skimage.io.imread


def numpy_reader():
    # lazy load numpy
    import numpy

    return numpy.load


class ImageFormat(enum.Enum):
    TIFF = (skimage_reader, "tiff", {"tif"})
    NUMPY = (numpy_reader, "npy")

    def __init__(self, reader_func, file_ext, alternate_extensions=None):
        self._reader_func = reader_func
        self._file_ext = file_ext
        self._alternate_extensions = set() if alternate_extensions is None else alternate_extensions

    @staticmethod
    def find_by_extension(extension):
        for imageformat in ImageFormat.__members__.values():
            if extension.lower() == imageformat._file_ext.lower():
                return imageformat
            for alternate_extension in imageformat._alternate_extensions:
                if extension.lower() == alternate_extension.lower():
                    return imageformat

        raise ValueError("Cannot find file format to match extension {}".format(extension))

    @property
    def reader_func(self):
        return self._reader_func()

    @property
    def file_ext(self):
        return self._file_ext
