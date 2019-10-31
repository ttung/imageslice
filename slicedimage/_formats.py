import enum


def tiff_reader():
    from imageio import imread

    def reader(f):
        return imread(f, format="tiff")

    return reader


def png_reader():
    from imageio import imread

    def reader(f):
        return imread(f, format="png")

    return reader


def numpy_reader():
    # lazy load numpy
    import numpy as np

    return np.load


def tiff_writer():
    """
    Return a method that accepts (file, array) and saves it to the file.  File may be a file-like
    object, str, or pathlib.Path.
    """
    from imageio import imwrite

    def writer(f, arr):
        imwrite(f, arr, format="tiff")

    return writer


def png_writer():
    from imageio import imwrite

    def writer(f, arr):
        return imwrite(f, arr, format="png")

    return writer


def numpy_writer():
    """
    Return a method that accepts (file, array) and saves it to the file.  File may be a file-like
    object, str, or pathlib.Path.
    """
    # lazy load numpy
    import numpy as np

    return np.save


class ImageFormat(enum.Enum):
    """
    The ImageFormat Enum exposes reading and writing methods for each enumerated object.

    To add a new object, assign to a name (e.g., NEW_FORMAT) a 4-tuple of (reader_provider,
    writer_provider, file_extension, {alternative_extensions}).
    """
    TIFF = (tiff_reader, tiff_writer, "tiff", {"tif"})
    NUMPY = (numpy_reader, numpy_writer, "npy", None)
    PNG = (png_reader, png_writer, "png", None)

    def __init__(
            self,
            reader_func,
            writer_func,
            file_ext,
            alternate_extensions,
    ):
        self._reader_func = reader_func
        self._writer_func = writer_func
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
    def writer_func(self):
        return self._writer_func()

    @property
    def file_ext(self):
        return self._file_ext
