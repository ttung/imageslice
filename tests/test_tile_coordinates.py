import unittest

from slicedimage import Tile


class TestTileCoordinates(unittest.TestCase):
    def test_tuple_to_tuple(self):
        tile = Tile(
            {
                'coord': (0, 1),
            },
            {},
        )
        self.assertEqual(tile.coordinates['coord'], (0, 1))

    def test_list_to_tuple(self):
        tile = Tile(
            {
                'coord': [0, 1],
            },
            {},
        )
        self.assertEqual(tile.coordinates['coord'], (0, 1))

    def test_scalar_to_tuple(self):
        tile = Tile(
            {
                'coord': 0,
            },
            {},
        )
        self.assertEqual(tile.coordinates['coord'], (0, 0))

    def test_single_scalar_in_tuple(self):
        with self.assertRaises(ValueError):
            Tile(
                {
                    'coord': (0,),
                },
                {},
            )

    def test_long_tuple(self):
        with self.assertRaises(ValueError):
            Tile(
                {
                    'coord': (0, 1, 2),
                },
                {},
            )


if __name__ == "__main__":
    unittest.main()
