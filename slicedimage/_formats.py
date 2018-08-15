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
    NUMPY = (numpy_reader, "npy", {}, True)

    def __init__(
            self,
            reader_func,
            file_ext,
            alternate_extensions,
            requires_seekable_file_handles=False,
    ):
        self._reader_func = reader_func
        self._file_ext = file_ext
        self._alternate_extensions = set() if alternate_extensions is None else alternate_extensions
        self._requires_seekable_file_handles = requires_seekable_file_handles

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

    @property
    def requires_seekable_file_handles(self):
        """
        The reader method of some file formats require the ability to seek inside the file.  If this
        is True, we will buffer the data so it is possible to seek.
        """
        return self._requires_seekable_file_handles
