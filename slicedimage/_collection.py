from __future__ import absolute_import, division, print_function, unicode_literals

from ._tileset import TileSet


class Collection(object):
    def __init__(self, extras=None):
        self.extras = extras
        self._partitions = dict()

    def validate(self):
        pass

    def add_partition(self, name, partition):
        self._partitions[name] = partition

    def all_tilesets(self):
        """
        Return all tilesets in this collection, directly or indirectly, as (name, tileset) tuples.
        """
        for name, partition in self._partitions.items():
            if isinstance(partition, Collection):
                for descendant_name, descendant_tileset in partition.all_tilesets():
                    yield descendant_name, descendant_tileset
            elif isinstance(partition, TileSet):
                yield name, partition

    def find_tileset(self, name):
        for partition_name, image_partition in self.all_tilesets():
            if name == partition_name:
                return image_partition
        return None

    def tiles(self, filter_fn=lambda _: True):
        result = []
        for partion_name, image_partition in self.all_tilesets():
            result.extend(image_partition.tiles(filter_fn))
        return result
