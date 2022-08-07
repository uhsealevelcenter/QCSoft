import os
import unittest

import numpy as np

from main import load_station_data

dirname = os.path.dirname(__file__)
input_filename = os.path.join(dirname, 'test_data/monp/ssaba1810.dat')
tmp_dir = os.path.join(dirname, 'test_data/ts_file_tmp')
# The ground truth output file. Produced by an earlier, better tested software version (0.6)
# Todo: Ask Fee to produce a ts, hourly, and daily file for an arbitrary station (without cleaning it) and use that output file as the ground truth
output_filename = os.path.join(dirname, 'test_data/ts_file_truth/t1231810.dat')


class TestDatFileSave(unittest.TestCase):
    input_data = {}
    output_data = {}

    def setUp(self) -> None:
        self.input_data = load_station_data([input_filename])
        self.output_data = load_station_data([output_filename])

    def tearDown(self) -> None:
        pass

    def test_ts_file_save(self):
        # Todo:
        # 1) Load the ground truth ts file (the one you get from Fee)
        # 2) Load the monp file for the same station and month
        # 3) Save the monp file to ts (without any cleaning)
        # 4) Compare the data for each sensor
        # 5) Somehow also compare that formatting is exactly the same, it's all strings after all
        # 6) Do similar steps for daily, and hourly

        # Check if PRS data is equal upon saving
        prs_data_in = self.input_data['PRS'].get_flat_data()
        prs_data_out = self.output_data['PRS'].get_flat_data()
        prs_data_is_equal = np.allclose(prs_data_in, prs_data_out)
        self.assertTrue(prs_data_is_equal)


if __name__ == '__main__':
    unittest.main()
