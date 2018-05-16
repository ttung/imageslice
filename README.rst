===================
Sliced imaging data
===================

Background
==========

If we want to store imaging data on the cloud and allow scientists to experiment with this data with interactive local tools (e.g., Jupyter notebooks), we should provide an easy interface to retrieve this data.  We should future-proof this model for extremely large images with multiple dimensions, where users may want to pull slices of this data without having to download the entire image.

Design
------

Images will be stored in a tiled format such that ranged requests can be used to efficiently fetch slices of the data.  The tiles of the image is described by a manifest, which is itself broken up into multiple files for easy consumption.

There should be a python API that allows users to point at an image set, ranges across multiple dimensions, and yields the data in numpy format.  The python API should retrieve the table of contents, calculate the objects needed, fetch them in parallel, decode them, and slice out the data needed.

Locating a tile
~~~~~~~~~~~~~~~

The location for each tile is given in coordinates and indices.  Coordinates is the location of the tile in geometric space, and indices is the location of the tile in non-geometric space.  Together, coordinates and indices resolve exactly where the tile is in the n-dimensional space.

Format
------

Each image should have a manifest, which is a hierarchical tree of JSON table-of-contents documents.  The leaf documents (`Image partition`_) contain a list of tiles.  The non-leaf documents (`TOC partition`_) contain a map from an arbitrary unique name (within the space of the entire image) to relative paths or URLs containing either other `TOC partitions`__ or `image partitions`__.

__ `TOC partition`_
__ `Image partition`_

.. _`TOC partition`:

TOC partition
~~~~~~~~~~~~~

TOC partitions should have the following fields:

===================  ======  ========  =================================================================================
Field Name           Type    Required  Description
-------------------  ------  --------  ---------------------------------------------------------------------------------
version              string  Yes       Semantic versioning of the file format.
tocs                 dict    Yes       Map of names to relative paths or URLs of `image partitions`__ or
                                       `TOC partition`__.
extras               dict    No        Additional application-specific payload.  The vocabulary and the schema are
                                       uncontrolled.
===================  ======  ========  =================================================================================

__ `Image partition`_
__ `TOC partition`_

.. _`Image partition`:

Image partition
~~~~~~~~~~~~~~~

Image partitions should have the following fields:

===================  ======  ========  =================================================================================
Field Name           Type    Required  Description
-------------------  ------  --------  ---------------------------------------------------------------------------------
version              string  Yes       Semantic versioning of the file format.
dimensions           list    Yes       Names of the dimensions.  Dimensions must include `x` and `y`.
tiles                dict    Yes       See Tiles_
shape                dict    Yes       Maps each non-geometric dimension to the possible number of values for that
                                       dimension for the tiles in this `Image partition TOC`_.
default_tile_shape   tuple   No        Default pixel dimensions of a tile, ordered as x, y.
default_tile_format  string  No        Default file format of the tiles.
zoom                 dict    No        See Zoom_
extras               dict    No        Additional application-specific payload.  The vocabulary and the schema are
                                       uncontrolled.
===================  ======  ========  =================================================================================

.. _Tiles:

Tiles
~~~~~

Each item in the tiles section describes a file:

============  ======  ========  ========================================================================================
Field Name    Type    Required  Description
------------  ------  --------  ----------------------------------------------------------------------------------------
file          string  Yes       Relative path to the file.
coordinates   dict    Yes       Maps each of the dimensions in geometric space, either `x`, `y`, or `z`, to either a
                                single dimension value, or a tuple specifying the range for that dimension.  The `x` and
                                `y` coordinates must be provided as ranges.   Each of the dimensions here must be
                                specified in the `Image partition TOC`_.
indices       dict    Yes       Maps each of the dimensions *not* in geometric space to the value for this tile.  Each
                                of the dimensions here must be specified in the `Image partition TOC`_.  The values of
                                the indices must be non-negative integers, and every value up to but not including the
                                maximum specified in the `shape` field of the `Image partition TOC`_ must be
                                represented.
tile_shape    tuple   No        Pixel dimensions of a tile, ordered as x, y.  If this is not provided, it defaults to
                                `default_tile_shape` in the `Image partition TOC`_).  If neither is provided, the tile
                                shape is inferred from actual file.
tile_format   string  No        File format of the tile.  If this is not provided, it defaults to `default_tile_format`
                                in the `Image partition TOC`_).  If neither is provided, the tile format is inferred
                                from actual file.
sha256        string  No        SHA256 checksum of the tile data.
extras        dict    No        Additional application-specific payload.  The vocabulary and the schema are
                                uncontrolled.
============  ======  ========  ========================================================================================

.. _Zoom:

Zoom
~~~~
