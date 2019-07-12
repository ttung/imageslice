class CommonPartitionKeys:
    VERSION = "version"
    EXTRAS = "extras"


class CollectionKeys(CommonPartitionKeys):
    CONTENTS = "contents"


class TileSetKeys(CommonPartitionKeys):
    DIMENSIONS = "dimensions"
    SHAPE = "shape"
    DEFAULT_TILE_SHAPE = "default_tile_shape"
    DEFAULT_TILE_FORMAT = "default_tile_format"
    TILES = "tiles"
    ZOOM = "zoom"


class TileKeys:
    FILE = "file"
    COORDINATES = "coordinates"
    INDICES = "indices"
    TILE_SHAPE = "tile_shape"
    TILE_FORMAT = "tile_format"
    SHA256 = "sha256"
    EXTRAS = "extras"
