from __future__ import absolute_import, division, print_function, unicode_literals

from ._imagepartition import ImagePartition


class TocPartition(object):
    def __init__(self, extras=None):
        self.extras = extras
        self._tocs = list()

    def validate(self):
        pass

    def add_toc(self, toc):
        self._tocs.append(toc)

    def all_tocs(self):
        """Return all TOCs referenced by this TOC, directly or indirectly."""
        result = []
        for toc in self._tocs:
            if isinstance(toc, TocPartition):
                result.extend(toc.all_tocs())
            elif isinstance(toc, ImagePartition):
                result.append(toc)
        return result

    def tiles(self, filter_fn=lambda _: True):
        result = []
        for toc in self.all_tocs():
            result.extend(toc.tiles(filter_fn))
        return result
