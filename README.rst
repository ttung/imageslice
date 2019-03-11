===================
Sliced imaging data
===================

Background
==========

If we want to store imaging data on the cloud and allow scientists to experiment with this data with interactive local tools (e.g., Jupyter notebooks), we should provide an easy interface to retrieve this data.  We should future-proof this model for extremely large image sets with multiple dimensions, where users may want to pull slices of this data without having to download the entire image set.

Design
------

An image set will be stored in a tiled format such that ranged requests can be used to efficiently fetch slices of the data.  The tiles of the image set is described by a manifest, which is itself broken up into multiple files for easy consumption.

There should be a python API that allows users to point at an image set, ranges across multiple dimensions, and yields the data in numpy format.  The python API should retrieve the table of contents, calculate the objects needed, fetch them in parallel, decode them, and slice out the data needed.

Locating a tile
~~~~~~~~~~~~~~~

The location for each tile is given in coordinates and indices.  Coordinates is the location of the tile in geometric space, and indices is the location of the tile in non-geometric space.  Together, coordinates and indices resolve exactly where the tile is in the n-dimensional space.

Manifest
--------

Each image set is described by a manifest, which is a hierarchical tree of JSON table-of-contents documents.  The leaf documents (`tile sets`__) describe a list of tiles.  The non-leaf documents (`collections`__) contain a map from an arbitrary unique name (within the space of the entire image) to relative paths or URLs containing either other `collections`__ or `tile sets`__.

__ `Tile Set`_
__ `Collection`_
__ `Collection`_
__ `Tile Set`_

.. _`Collection`:

Collection
~~~~~~~~~~

A collection should have the following fields:

===================  ======  ========  =================================================================================
Field Name           Type    Required  Description
-------------------  ------  --------  ---------------------------------------------------------------------------------
version              string  Yes       Semantic versioning of the file format.
contents             dict    Yes       Map of names to relative paths or URLs of `collections`__ or `tile sets`__.
extras               dict    No        Additional application-specific payload.  The vocabulary and the schema are
                                       uncontrolled.
===================  ======  ========  =================================================================================

__ `Collection`_
__ `Tile Set`_

.. _`Tile Set`:

Tile Set
~~~~~~~~

A tile set should have the following fields:

===================  ======  ========  =================================================================================
Field Name           Type    Required  Description
-------------------  ------  --------  ---------------------------------------------------------------------------------
version              string  Yes       Semantic versioning of the file format.
dimensions           list    Yes       Names of the dimensions.  Dimensions must include `x` and `y`.
tiles                dict    Yes       See Tiles_
shape                dict    Yes       Maps each non-geometric dimension to the possible number of values for that
                                       dimension for the tiles in this `Tile Set`_.
default_tile_shape   dict    No        Mapping from the pixel dimensions to their sizes.
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
                                specified in the `Tile Set`_.
indices       dict    Yes       Maps each of the dimensions *not* in geometric space to the value for this tile.  Each
                                of the dimensions here must be specified in the `Tile Set`_.  The values of the indices
                                must be non-negative integers, and every value up to but not including the maximum
                                specified in the `shape` field of the `Tile Set`_ must be represented.
tile_shape    dict    No        Mapping from the pixel dimensions to their sizes.  If this is not provided, it defaults
                                to `default_tile_shape` in the `Tile Set`_).  If neither is provided, the tile shape is
                                inferred from actual file.
tile_format   string  No        File format of the tile.  If this is not provided, it defaults to `default_tile_format`
                                in the `Tile Set`_).  If neither is provided, the tile format is inferred from actual
                                file.
sha256        string  No        SHA256 checksum of the tile data.
extras        dict    No        Additional application-specific payload.  The vocabulary and the schema are
                                uncontrolled.
============  ======  ========  ========================================================================================

.. _Zoom:

Zoom
~~~~
