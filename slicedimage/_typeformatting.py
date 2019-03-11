import enum


def format_tile_coordinates(tile_dimensions):
    """
    Given a dictionary mapping keys to values, where the keys may either be strings or enums, and
    the values may either be a scalar number or an iterable of two scalar numbers, return a new
    dictionary with the same contents, except the keys are converted to strings, and the value is
    transformed as per the following rules:

    scalar_number -> (scalar_number, scalar_number)
    [scalar_number_0, scalar_number_1] -> (scalar_number_0, scalar_number_1)
    """
    result = dict()
    for name, value in tile_dimensions.items():
        key = _str_or_enum_to_str(name)
        try:
            iter(value)
            value = tuple(value)
            if len(value) == 2:
                result[key] = value
            else:
                raise ValueError("Not a valid input")
        except TypeError:
            result[key] = (value, value)
    return result


def format_enum_keyed_dicts(enum_keyed_dict):
    """
    Given a dictionary mapping keys to values, where the keys may either be strings or enums,
    return a new dictionary with the same contents, except the keys are converted to strings.
    """
    result = dict()
    for name, value in enum_keyed_dict.items():
        result[_str_or_enum_to_str(name)] = value
    return result


def format_tileset_dimensions(tileset_dimensions):
    """
    Given an iterable of strings or enums, return a frozenset consisting of the same values, except
    all converted to strings.
    """
    return frozenset(
        _str_or_enum_to_str(tileset_dimension)
        for tileset_dimension in tileset_dimensions)


def format_tileset_shape(d):
    """
    Given a dictionary mapping keys to values, where the keys may either be strings or enums, return
    a new dictionary where the keys are all converted to strings.
    """
    result = dict()
    for name, value in d.items():
        result[_str_or_enum_to_str(name)] = value
    return result


def _str_or_enum_to_str(value):
    """
    Given a scalar value or an enum, return the scalar value if it's a scalar value, or the enum's
    value field if it's an enum.
    """
    if isinstance(value, enum.Enum):
        return value.value
    else:
        return value
