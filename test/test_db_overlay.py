import unittest

from db_overlay.extract import build_db_request_spec
from db_overlay.spec import month_span_inclusive


class TestDbOverlaySpec(unittest.TestCase):

    def test_regular_file_spec(self):
        spec = build_db_request_spec(file_paths=[
            "/tmp/ssaba1811.dat",
            "/tmp/ssaba1812.dat",
            "/tmp/ssaba1901.dat",
        ])

        self.assertIsNotNone(spec)
        self.assertEqual(spec.station_key, "saba")
        self.assertEqual(spec.station_key_type, "uhslc_code")
        self.assertEqual(spec.start_yyyymm, 201811)
        self.assertEqual(spec.end_yyyymm, 201901)

    def test_ts_file_spec(self):
        spec = build_db_request_spec(file_paths=[
            "/tmp/t7952604.dat",
            "/tmp/t7952605.dat",
        ])

        self.assertIsNotNone(spec)
        self.assertEqual(spec.station_key, "795")
        self.assertEqual(spec.station_key_type, "uhslc_id")
        self.assertEqual(spec.start_yyyymm, 202604)
        self.assertEqual(spec.end_yyyymm, 202605)

    def test_mixed_station_files_return_none(self):
        spec = build_db_request_spec(file_paths=[
            "/tmp/ssaba1811.dat",
            "/tmp/schki1811.dat",
        ])

        self.assertIsNone(spec)

    def test_month_span_inclusive(self):
        self.assertEqual(month_span_inclusive(202604, 202605), 2)
        self.assertEqual(month_span_inclusive(202511, 202602), 4)


if __name__ == "__main__":
    unittest.main()
