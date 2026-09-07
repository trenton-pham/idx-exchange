from __future__ import annotations

import unittest

import geopandas as gpd
import pandas as pd
from pandas.api.types import is_bool_dtype
from shapely.geometry import box

from clean import flag_coordinates


class CoordinateFlagTests(unittest.TestCase):
    def setUp(self):
        self.county_boundaries = gpd.GeoDataFrame(
            {
                "COUNTY_NAME": ["Alpha", "Beta"],
                "geometry": [
                    box(-2, 0, -1, 1),
                    box(-1, 0, 0, 1),
                ],
            },
            crs="EPSG:4326",
        )

    def test_flags_county_mismatches_and_unverifiable_coordinates(self):
        source = pd.DataFrame(
            {
                "CountyOrParish": [
                    "Alpha",
                    "Alpha",
                    " beta ",
                    "Alpha",
                    " ALPHA ",
                    "Alpha",
                    "Alpha",
                    "Alpha",
                    "Alpha",
                    "Unknown County",
                    None,
                ],
                "Latitude": [
                    0.5,
                    0.5,
                    0.5,
                    0.5,
                    "0.5",
                    0.5,
                    None,
                    0.5,
                    95,
                    0.5,
                    0.5,
                ],
                "Longitude": [
                    -1.5,
                    -0.5,
                    -0.5,
                    -1,
                    1.5,
                    -3,
                    -1.5,
                    "not-a-coordinate",
                    -1.5,
                    -1.5,
                    -1.5,
                ],
                "value": list(range(11)),
            },
            index=[8, 3, 3, 10, 2, 6, 4, 1, 12, 9, 7],
        )

        result = flag_coordinates(source, self.county_boundaries)

        self.assertEqual(result.index.tolist(), source.index.tolist())
        self.assertEqual(result["value"].tolist(), source["value"].tolist())
        self.assertEqual(
            result["coordinates_in_california"].tolist(),
            [True, True, True, True, True, False, False, False, False, True, True],
        )
        self.assertEqual(
            result["coordinates_outside_county_flag"].tolist(),
            [False, True, False, False, False, True, True, True, True, True, True],
        )
        self.assertEqual(result.iloc[4]["Longitude"], -1.5)

        self.assertTrue(is_bool_dtype(result["coordinates_in_california"]))
        self.assertTrue(is_bool_dtype(result["coordinates_outside_county_flag"]))
        self.assertEqual(len(result), len(source))

        temporary_columns = {
            "_row_id",
            "geometry",
            "index_right",
            "COUNTY_NAME",
            "_inside_california",
            "_county_match",
        }
        self.assertTrue(temporary_columns.isdisjoint(result.columns))


if __name__ == "__main__":
    unittest.main()
