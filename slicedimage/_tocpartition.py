from __future__ import absolute_import, division, print_function, unicode_literals

from ._imagepartition import ImagePartition


class TocPartition(object):
    def __init__(self, extras=None):
        self.extras = extras
        self._partitions = dict()

    def validate(self):
        pass

    def add_partition(self, name, partition):
        self._partitions[name] = partition

    def all_image_partitions(self):
        """Return all image partitions in this TOC partition, directly or indirectly, as (name, partition) tuples."""
        for name, partition in self._partitions.items():
            if isinstance(partition, TocPartition):
                for descendant_name, descendant_toc in partition.all_image_partitions():
                    yield descendant_name, descendant_toc
            elif isinstance(partition, ImagePartition):
                yield name, partition

    def find_image_partition(self, name):
        for partition_name, image_partition in self.all_image_partitions():
            if name == partition_name:
                return image_partition
        return None

    def tiles(self, filter_fn=lambda _: True):
        result = []
        for partion_name, image_partition in self.all_image_partitions():
            result.extend(image_partition.tiles(filter_fn))
        return result
